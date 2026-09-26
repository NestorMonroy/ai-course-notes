#!/usr/bin/env python3
"""El motor del ciclo de traducción es-MX (`docs/ES_MX_TRANSLATION_PLAN.md`).

    translation_loop.py prepare  --bench B <nota.tex>...
    translation_loop.py prompt   [--memory M] --out P.md
    translation_loop.py translate --bench B --model <id completo> [--width N] [--memfree TAM] [--timeout S]
    translation_loop.py usage    --bench B
    translation_loop.py plan     --out P.tsv
    translation_loop.py advance  --batch L --model <id> [--compile] [--max-iterations N]
    translation_loop.py triage   [--memory M]
    translation_loop.py measure  --decision D [--compile] [--jobs N]
    translation_loop.py retranslate --batch L
    translation_loop.py cycle    --batch L --model <id> [--compile] <nota.tex>...
    translation_loop.py assemble --bench B
    translation_loop.py verify   --out S.jsonl [--compile] [--jobs N] <nota.es-mx.tex>...
    translation_loop.py sweep    --bench B --iteration N [--memory M] [--jobs N]

La unidad del traductor es el FRAGMENTO: el cuerpo de la nota partido por
`\\section` (y por `\\subsection` si una sección es larga). Así una nota grande
no depende de lo que una conversación alcanza a escribir de una vez, y solo se
retraduce el fragmento que falla.

El traductor es `headless-pool` de THYROX vía `tools/thyrox/run` (un `claude -p`
por fragmento, repartidos con GNU Parallel); `TRANSLATION_RUNNER` lo sustituye
en las pruebas. La verificación reparte las notas con GNU Parallel y guarda
cada veredicto en `$THYROX_CACHE_DIR/translation/`, con clave en el contenido
de la nota zh, la es-MX y los verificadores.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

LANG_DIR = REPO_ROOT / "tools" / "lang" / "es-mx"
DEFAULT_MEMORY = LANG_DIR / "translation_memory.jsonl"
PROMPT_TEMPLATE = LANG_DIR / "translator_prompt.md"
CHUNK_LIMIT = 12000  # caracteres; una sección mas larga se parte por \subsection
HAN = re.compile(r"[\u4e00-\u9fff]")
COMMENT_LINE = re.compile(r"(?<!\\)%.*$", re.M)
PARENTHESIZED = re.compile(r"[(（][^()（）\n]*[)）]")
FULL_MODEL_ID = re.compile(r"^claude-[a-z]+-\d")
VERIFIERS = ["check_translation_parity.py", "check_prose_vocabulary.py", "check_note_coverage.py",
             "note_language.py", "translation_loop.py"]


# --- utilidades -----------------------------------------------------------

def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def es_path(zh: Path) -> Path:
    return zh.with_name(zh.name[:-len(".tex")] + ".es-mx.tex")


def zh_path(es: Path) -> Path:
    return es.with_name(es.name[:-len(".es-mx.tex")] + ".tex")


def has_residual_han(text: str) -> bool:
    return any(HAN.search(PARENTHESIZED.sub("", line)) for line in text.splitlines())


INCLUDE = re.compile(r"\\(?:input|include)\{([^}]+?)\}")


def map_inputs(text: str) -> str:
    text = re.sub(r"\\(input|include)\{([^}]+?)(?<!\.es-mx)(\.tex)?\}",
                  lambda m: f"\\{m.group(1)}{{{m.group(2)}.es-mx.tex}}", text)
    # `\IfFileExists{x.tex}{\input{x.tex}}{}` miraba el capítulo zh: la condición
    # no dependía de que existiera su traducción.
    return re.sub(r"\\IfFileExists\{([^}]+?)(?<!\.es-mx)\.tex\}",
                  lambda m: f"\\IfFileExists{{{m.group(1)}.es-mx.tex}}", text)


def included_files(text: str, base: Path) -> list[Path]:
    """Los archivos que la nota incluye con `\\input`/`\\include`, desde `base`.

    XeLaTeX los resuelve desde el directorio de la nota principal, también los
    anidados; por eso la base es siempre la de la nota, no la del capítulo.
    """
    found = []
    for match in INCLUDE.finditer(text):
        name = match.group(1)
        path = base / (name if name.endswith(".tex") else name + ".tex")
        if path.is_file() and not path.name.endswith(".es-mx.tex"):
            found.append(path.resolve())
    return found


def split_body(body: str) -> list[str]:
    """Fragmentos: lo anterior a la primera sección, y una por sección."""
    parts = re.split(r"(?m)^(?=\\section\*?\{)", body)
    chunks: list[str] = []
    for part in parts:
        if len(part) <= CHUNK_LIMIT:
            chunks.append(part)
            continue
        chunks.extend(p for p in re.split(r"(?m)^(?=\\subsection\*?\{)", part) if p)
    return chunks


# --- prepare --------------------------------------------------------------

SOURCE_PATTERNS = ("*.en.srt", "*.en-orig.srt", "*.srt")


def english_source(note_dir: Path) -> Path | None:
    """La transcripción original en inglés de la clase, si la hay.

    Las notas zh traducen clases dadas en inglés: la transcripción dice qué
    término usó quien habló. Se prefiere `.en.srt`; un `.srt` sin sufijo cuenta
    solo si su texto es inglés (los podcasts de Zhang Xiaojun son en chino).
    """
    for pattern in SOURCE_PATTERNS:
        for path in sorted(note_dir.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
            letters = sum(ch.isascii() and ch.isalpha() for ch in text)
            if letters and len(HAN.findall(text)) < letters * 0.05:
                return path
    return None


def cmd_prepare(args) -> int:
    from localize_preamble import localize
    root = Path.cwd()
    bench = args.bench
    (bench / "chunks").mkdir(parents=True, exist_ok=True)
    units, notes = [], []
    # Cada nota con sus capítulos incluidos: un capítulo es una unidad más, con
    # su propio `.es-mx.tex`, y la nota apunta a él por `map_inputs`.
    queue = [(Path(zh).resolve(), Path(zh).resolve().parent) for zh in args.notes]
    seen: set[Path] = set()
    while queue:
        zh, base = queue.pop(0)
        if zh in seen:
            continue
        seen.add(zh)
        original = zh.read_text(encoding="utf-8")
        queue += [(child, base) for child in included_files(original, base)]
        note_id = rel(zh, root)[:-len(".tex")].replace("/", "__")
        # `localize` reescribe preámbulos; en un capítulo sin `\documentclass` sus
        # reglas de metadatos caían sobre la prosa (`。` → `.` en el cuerpo).
        text = map_inputs(localize(original) if "\\documentclass" in original else original)
        marker = "\\begin{document}"
        cut = text.find(marker)
        if cut >= 0:
            cut = text.index("\n", cut) + 1
        else:
            cut = 0
        head, body = text[:cut], text[cut:]
        out = bench / "chunks" / note_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "head.tex").write_text(head, encoding="utf-8")
        source = english_source(zh.parent)
        link = out / "source.srt"
        if link.is_symlink() or link.exists():
            link.unlink()
        if source is not None:
            link.symlink_to(os.path.relpath(source, out))
        if HAN.search(COMMENT_LINE.sub("", head)):
            # Lo que el script no localiza del preámbulo (`\notetitle`, que es
            # prosa y va en la portada) se traduce como una unidad mas: la
            # fuente latina no tiene esos glifos y XeLaTeX los omitiria en silencio.
            (out / "head.zh.tex").write_text(head, encoding="utf-8")
            units.append("\t".join([rel(zh, root), note_id, "head", str(out / "head.zh.tex"), str(out / "head.es.tex")]))
        for k, chunk in enumerate(split_body(body)):
            zh_chunk = out / f"{k:03d}.zh.tex"
            zh_chunk.write_text(chunk, encoding="utf-8")
            units.append("\t".join([rel(zh, root), note_id, f"{k:03d}", str(zh_chunk), str(out / f"{k:03d}.es.tex")]))
        notes.append("\t".join([rel(zh, root), note_id, str(es_path(zh)), str(base)]))
    (bench / "units.tsv").write_text("\n".join(units) + "\n", encoding="utf-8")
    (bench / "notes.tsv").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(f"prepare: {len(notes)} nota(s), {len(units)} fragmento(s) en {bench}")
    return 0


# --- prompt ---------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def cited(forms: str | None) -> str:
    """Las formas rechazadas como citas (`a`, `b`): se nombran para prohibirlas."""
    items = [f.strip() for f in (forms or "").split("|") if f.strip()]
    return ", ".join(f"`{f}`" for f in items) or "—"


def build_prompt(memory: Path) -> str:
    import csv
    from note_language import ES_MX, ZH
    parts = [PROMPT_TEMPLATE.read_text(encoding="utf-8").rstrip(), "", "## Glosario (obligatorio)", "",
             "| Término | Decisión | Forma es-MX | Significado | Formas prohibidas |", "|---|---|---|---|---|"]
    with (LANG_DIR / "glossary.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            parts.append(f"| {row['term_en']} | {row['decision']} | {row.get('es_mx') or '—'} | "
                         f"{row.get('meaning') or ''} | {cited(row.get('rejected'))} |")
    import check_translation_parity as parity
    phrases = parity.fixed_phrases(LANG_DIR / "phrases.tsv")
    if phrases:
        parts += ["", "## Frases fijas (se traducen siempre así, en todas las notas)", ""]
        parts += [f"- `{zh}` → `{es}`" for zh, es in phrases]
    parts += ["", "## Etiquetas de estructura (se traducen siempre así)", ""]
    parts += [f"- `{zh}` → `{es}`" for zh, es in [
        (ZH.section_summary_title, ES_MX.section_summary_title),
        (ZH.final_section_title, ES_MX.final_section_title),
        ("拓展阅读", "Lecturas adicionales"), ("读图", "Lectura de la figura"),
        ("背景概念", "Concepto previo"), ("术语表", "Glosario"), ("术语消化", "Términos clave"),
        ("课堂提示", "Nota de clase"), ("老师强调", "el docente enfatiza"), ("来源", "Fuente")]]
    # La lista entera de `prohibited_forms.txt`, citada: con solo tres clichés de
    # ejemplo, «la clave está en» sobrevivió a una retraducción (cs329a, it. 02).
    import check_prose_vocabulary as prose
    forbidden = prose.load_forbidden(prose.DEFAULT_FORBIDDEN)
    parts += ["", "## Formas prohibidas (no aparecen en la traducción)", "",
              ", ".join(f"`{form}`" + (f" → {sub}" if sub else "") for form, sub in forbidden)]
    rules = [e["fix_generico"].get("regla", "") for e in read_jsonl(memory)
             if isinstance(e.get("fix_generico"), dict) and e["fix_generico"].get("tipo") == "prompt"]
    if rules:
        parts += ["", "## Reglas aprendidas en lotes anteriores (obligatorias)", ""] + [f"- {r}" for r in rules if r]
    return "\n".join(parts) + "\n"


def cmd_prompt(args) -> int:
    args.out.write_text(build_prompt(args.memory), encoding="utf-8")
    print(f"prompt: {args.out}")
    return 0


# --- translate ------------------------------------------------------------

def pending_units(bench: Path) -> list[list[str]]:
    rows = [l.split("\t") for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    pending = []
    for row in rows:
        es = Path(row[4])
        zh_text = Path(row[3]).read_text(encoding="utf-8")
        if not es.is_file() or (has_residual_han(es.read_text(encoding="utf-8")) and HAN.search(zh_text)):
            pending.append(row)
    return pending


# La memoria del pool la hace cumplir GNU Parallel mientras corre (`--memfree`
# de headless-pool, THYROX bfb4eb15): no lanza un ítem bajo la cota y reencola
# el mas joven si la memoria baja de la mitad. 3G deja lugar a un `tsc` de 2 GB
# en paralelo. La anchura NO se deriva de la carga —la carga a un minuto mide a
# los otros procesos, no al pool—: solo acota la concurrencia contra la API,
# cuyos limites de tasa no se ven desde el contenedor. 10 es lo que el piloto
# corrió sin un 429; si aparece uno, se baja con `--width`.
DEFAULT_MEMFREE = "3G"
# Con `Grep` sobre `source.srt`, la ola 1 midió 46 ítems en 2 turnos, 19 en 3,
# 10 en 4 y 18 que agotaron el tope de 4 (`error_max_turns`): el doble cubre esa cola.
MAX_TURNS = 8
DEFAULT_WIDTH = 10
BEGIN_MARK, END_MARK = "<<<ES", "ES>>>"


def extract_translation(result: str) -> str | None:
    """El fragmento traducido que el modelo devuelve entre marcadores."""
    match = re.search(rf"^{re.escape(BEGIN_MARK)}\n(.*?)\n?^{re.escape(END_MARK)}\s*$", result or "", re.M | re.S)
    return match.group(1) + "\n" if match else None


ENVIRONMENT = re.compile(r"\\(begin|end)\{([^}]+)\}")


def environments(text: str) -> collections.Counter:
    """El multiconjunto de `\\begin{x}` y `\\end{x}` de un fragmento."""
    return collections.Counter(ENVIRONMENT.findall(COMMENT_LINE.sub("", text)))


def structure_problem(zh: str, es: str) -> str | None:
    """Qué entornos cambió la traducción, o None si los conserva todos.

    cs329a, iteración 04: un fragmento volvió sin un `\\begin{itemize}` y la
    nota dejó de compilar. Se mide al recibir el fragmento, antes de escribirlo.
    """
    # Ola 3: el modelo partió un carácter multibyte («est��» por «está»).
    if "\ufffd" in es and "\ufffd" not in zh:
        return "carácter de reemplazo U+FFFD"
    a, b = environments(zh), environments(es)
    if a == b:
        return None
    return ", ".join(sorted({name for _kind, name in (a - b) + (b - a)}))


# La respuesta de `claude -p` cuando la cuenta agotó su cuota (ola 2):
# «You've hit your session limit · resets 4am (UTC)», con `subtype: success`.
SESSION_LIMIT = re.compile(r"hit your (?:\w+ )?limit", re.I)


def limit_reached(out_dir: Path) -> str | None:
    """La respuesta de límite de la cuenta, si alguna del pool la trae."""
    for result_file in sorted(out_dir.glob("*.json")):
        try:
            result = json.loads(result_file.read_text(encoding="utf-8")).get("result") or ""
        except (OSError, ValueError, AttributeError):
            continue
        if SESSION_LIMIT.search(result) and "<<<ES" not in result:
            return result.strip()[:120]
    return None


def collect_results(out_dir: Path, targets: dict[str, str]) -> list[str]:
    """Escribe cada fragmento traducido; devuelve los ítems rechazados.

    Se rechaza el que vuelve sin marcadores y el que no conserva los entornos
    del original; los dos quedan pendientes.
    """
    missing = []
    index = out_dir / "index.tsv"
    rows = [l.split("\t", 1) for l in index.read_text(encoding="utf-8").splitlines() if l.strip()] if index.is_file() else []
    for n, zh in rows:
        result_file = out_dir / f"{n}.json"
        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        result = data.get("result", "") or ""
        text = extract_translation(result)
        if text is None:
            # La causa, si `claude -p` la da (`error_max_turns` en la ola 1).
            reason = data.get("subtype") or ("sin salida" if not data else "respuesta sin marcadores")
            print(f"translate: rechazado ({reason}): {zh}", file=sys.stderr)
            missing.append(zh)
            continue
        problem = structure_problem(Path(zh).read_text(encoding="utf-8"), text)
        if problem:
            print(f"translate: la estructura de entornos cambió ({problem}): {zh}", file=sys.stderr)
            missing.append(zh)
            continue
        Path(targets[zh]).write_text(text, encoding="utf-8")
    return missing


def cmd_translate(args) -> int:
    if not FULL_MODEL_ID.match(args.model):
        print(f"translate: `{args.model}` no es un identificador completo (claude-<familia>-<version>); "
              "headless-pool rechaza alias.", file=sys.stderr)
        return 2
    pending = pending_units(args.bench)
    # Un fragmento sin chino (la portada ya localizada por script) se copia: el
    # piloto pago una conversación entera para oír que no había nada que traducir.
    plain = [row for row in pending if not HAN.search(Path(row[3]).read_text(encoding="utf-8"))]
    for row in plain:
        shutil.copyfile(row[3], row[4])
    pending = [row for row in pending if row not in plain]
    print(f"translate: {len(pending)} fragmento(s) por traducir; sin chino: {len(plain)} (copiados)", file=sys.stderr)
    if not pending:
        return 0
    prompt = args.bench / "prompt.md"
    prompt.write_text(build_prompt(args.memory), encoding="utf-8")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = args.bench / "translate" / stamp
    runner = os.environ.get("TRANSLATION_RUNNER", str(REPO_ROOT / "tools" / "thyrox" / "run"))
    cmd = [runner, "headless-pool", "--prompt", str(prompt), "--out", str(out_dir),
           "--model", args.model, "--tools", "Read,Grep", "--width", str(args.width), "--memfree", args.memfree,
           "--timeout", str(args.timeout), "--max-turns", str(MAX_TURNS), "--cwd", str(Path.cwd())]
    print(f"translate: width={args.width} memfree={args.memfree}", file=sys.stderr)
    code = subprocess.run(cmd, input="".join(f"{row[3]}\n" for row in pending), text=True).returncode
    missing = collect_results(out_dir, {row[3]: row[4] for row in pending})
    limit = limit_reached(out_dir)
    if limit:
        # Contra el límite de la cuenta no hay reintento útil: en la ola 2,
        # 105 de 117 rechazos eran esta respuesta, reintentada tres veces.
        print(f"translate: límite de sesión de la cuenta («{limit}»); se detiene sin reintentar",
              file=sys.stderr)
        return 5
    for zh in missing:
        print(f"translate: sin marcadores {BEGIN_MARK}/{END_MARK}: {zh}", file=sys.stderr)
    return 1 if missing or code else 0


# --- usage ----------------------------------------------------------------

# Copiados de THYROX `src/transcript/usage.py` (feature/ai-course-notes-l1):
# los cuatro tipos de token que se facturan por separado. El ciclo reporta
# tokens y no dinero: el peso de cada componente es del contrato de precio.
COMPONENTS = ("input", "cache_creation", "cache_read", "output")
USAGE_KEYS = {"input": "input_tokens", "cache_creation": "cache_creation_input_tokens",
              "cache_read": "cache_read_input_tokens", "output": "output_tokens"}
LATIN_LETTER = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")


def cmd_usage(args) -> int:
    targets = {row[3]: row[4] for row in
               (l.split("\t") for l in (args.bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip())}
    rows, totals, han_sum, letter_sum = [], dict.fromkeys(COMPONENTS, 0), 0, 0
    runs = getattr(args, "runs", None)
    indexes = [r / "index.tsv" for r in runs] if runs is not None else sorted(args.bench.glob("translate/*/index.tsv"))
    for index in (i for i in indexes if i.is_file()):
        for line in index.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            n, zh = line.split("\t", 1)
            try:
                usage = json.loads((index.parent / f"{n}.json").read_text(encoding="utf-8")).get("usage", {})
            except (OSError, ValueError):
                usage = {}
            counts = {c: int(usage.get(USAGE_KEYS[c], 0) or 0) for c in COMPONENTS}
            han = len(HAN.findall(Path(zh).read_text(encoding="utf-8")))
            es = Path(targets.get(zh, ""))
            letters = len(LATIN_LETTER.findall(es.read_text(encoding="utf-8"))) if es.is_file() else 0
            if letters:
                han_sum, letter_sum = han_sum + han, letter_sum + letters
            rows.append([Path(zh).name, str(han), str(letters), *(str(counts[c]) for c in COMPONENTS)])
            for c in COMPONENTS:
                totals[c] += counts[c]
    header = ["chunk", "han", "letters", *COMPONENTS]
    (getattr(args, "out", None) or args.bench / "usage.tsv").write_text("\n".join("\t".join(r) for r in [header, *rows]) + "\n", encoding="utf-8")
    ratio = letter_sum / han_sum if han_sum else 0.0
    print(f"items={len(rows)} " + " ".join(f"{c}={totals[c]}" for c in COMPONENTS) + f" letters_per_han={ratio:.2f}")
    return 0


# --- assemble -------------------------------------------------------------

GRAPHIC = re.compile(r"(\\includegraphics(?:\[[^\]]*\])?\{)([^}]+?)(\.png)(\})")


def localized_figures(text: str, note_dir: Path) -> str:
    """Apunta a `<figura>.es-mx.png` cuando existe (texto horneado traducido)."""
    def swap(m: re.Match) -> str:
        sibling = f"{m.group(2)}.es-mx{m.group(3)}"
        return m.group(1) + sibling + m.group(4) if (note_dir / sibling).is_file() else m.group(0)
    return GRAPHIC.sub(swap, text)


def cmd_assemble(args) -> int:
    rows = [l.split("\t") for l in (args.bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    notes = [l.split("\t") for l in (args.bench / "notes.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    missing = []
    for _zh, note_id, target, *base in notes:
        chunks = [r for r in rows if r[1] == note_id]
        absent = [r[4] for r in chunks if not Path(r[4]).is_file()]
        if absent:
            missing += absent
            continue
        heads = [r for r in chunks if r[2] == "head"]
        head_file = Path(heads[0][4]) if heads else args.bench / "chunks" / note_id / "head.tex"
        head = head_file.read_text(encoding="utf-8")
        body = "".join(Path(r[4]).read_text(encoding="utf-8")
                       for r in sorted((r for r in chunks if r[2] != "head"), key=lambda r: r[2]))
        # Las figuras de un capítulo se resuelven desde la nota que lo incluye.
        figures_dir = Path(base[0]) if base else Path(target).parent
        Path(target).write_text(localized_figures(head + body, figures_dir), encoding="utf-8")
    for m in missing:
        print(f"assemble: falta el fragmento traducido {m}", file=sys.stderr)
    print(f"assemble: {len(notes) - len({Path(m).parent for m in missing})} nota(s) ensamblada(s)")
    return 1 if missing else 0


# --- verify ---------------------------------------------------------------

def cache_dir() -> Path:
    base = os.environ.get("THYROX_CACHE_DIR") or str(REPO_ROOT / ".claude" / "cache")
    path = Path(base) / "translation"
    path.mkdir(parents=True, exist_ok=True)
    return path


VERIFIER_INPUTS = ("glossary.tsv", "prohibited_forms.txt", "prose_vocabulary_baseline.txt", "phrases.tsv",
                   "hunspell/es_MX.dic", "hunspell/es_MX.aff")


def fingerprint(compile_: bool) -> str:
    digest = hashlib.sha256(b"compile" if compile_ else b"")
    for name in VERIFIERS:
        digest.update((HERE / name).read_bytes())
    # Todo lo que el verificador lee de la carpeta del idioma: si cambia, el
    # veredicto guardado ya no vale (las frases fijas y el diccionario es_MX
    # quedaban fuera de la huella).
    for name in VERIFIER_INPUTS:
        path = LANG_DIR / name
        digest.update(name.encode() + (path.read_bytes() if path.is_file() else b""))
    return digest.hexdigest()


def compile_signal(es: Path) -> list[tuple[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        for _ in range(2):
            subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", tmp, es.name],
                           cwd=es.parent, capture_output=True, text=True, timeout=600)
        # El PDF solo no basta: con `-halt-on-error` las paginas ya enviadas
        # llegan al PDF aunque después haya un error (piloto cs329a/lecture01).
        pdf = Path(tmp) / (es.name[:-len(".tex")] + ".pdf")
        log = Path(tmp) / (es.name[:-len(".tex")] + ".log")
        lines = log.read_text(errors="ignore").splitlines() if log.is_file() else []
        at = next((i for i, l in enumerate(lines) if l.startswith("! ")), None)
        if at is not None or not (pdf.is_file() and pdf.stat().st_size > 0):
            if at is None:
                return [("compile:error", "sin PDF")]
            # La línea `l.NN …\comando` que sigue al error nombra lo que falló;
            # `retranslate` la usa para encontrar el fragmento.
            context = next((l for l in lines[at + 1:at + 6] if re.match(r"l\.\d+ ", l)), "")
            return [("compile:error", f"{lines[at][:120]} | {context[-80:]}".rstrip(" |"))]
        # Un glifo que la fuente no tiene no es un error de XeLaTeX: se omite
        # con un aviso y el PDF sale sin el texto (la portada del piloto).
        glyph = next((l for l in lines if l.startswith("Missing character")), None)
        return [("compile:missing-glyph", glyph[:160])] if glyph else []


def verify_notes(notes: list[Path], compile_: bool, root: Path, lexicons) -> tuple[list[dict], int]:
    import check_prose_vocabulary as prose
    from check_translation_parity import DEFAULT_GLOSSARY, compare
    es_lex, en_lex, lemmas, forbidden, keep, baseline = lexicons
    key_base = fingerprint(compile_)
    rows, hits = [], 0
    for es in notes:
        zh = zh_path(es)
        key = hashlib.sha256(key_base.encode() + zh.read_bytes() + es.read_bytes()).hexdigest()
        cached = cache_dir() / f"{key}.json"
        if cached.is_file():
            # El caché guarda el veredicto del contenido; la nota es la que se
            # verifica ahora. Dos notas con el mismo contenido compartían la ruta
            # de la primera y una causa compartida parecía local.
            rows += [{**r, "note": rel(es, root)} for r in json.loads(cached.read_text(encoding="utf-8"))]
            hits += 1
            continue
        zh_text = zh.read_text(encoding="utf-8")
        es_text = es.read_text(encoding="utf-8")
        found = compare(zh_text, es_text, DEFAULT_GLOSSARY)
        # El inglés que la nota zh ya escribe es término técnico que se queda
        # (`reward model`, opciones de tcolorbox); solo es defecto el que
        # introdujo la traducción.
        inherited_english = {w.lower() for w in re.findall(r"[A-Za-z]+", zh_text)}
        for k in prose.scan([es], es_lex, en_lex, forbidden, keep, root, lemmas):
            if k in baseline:
                continue
            if k.startswith("english:"):
                word = k.split(":", 1)[1]
                if word in inherited_english or prose.singulars(word) & inherited_english:
                    continue
                found.append((f"prose:{k}", ""))
            elif k.startswith("unaccented:"):
                # Una palabra inglesa del original (`precision`) no es una
                # palabra española sin tilde (`precisión`).
                if k.split(":", 1)[1] not in inherited_english:
                    found.append((f"prose:{k}", ""))
            elif k.startswith("spanglish:"):
                found.append((f"prose:{k}", ""))
            elif "::" in k:
                found.append((f"prose:forbidden:{k.split('::', 1)[1]}", ""))
            else:
                found.append((f"prose:invented:{k}", ""))
        # Un error de cobertura que el original ya tiene es deuda del original,
        # no un defecto de la traducción: solo sale lo que la traducción rompió.
        inherited = coverage_errors(zh)
        # Los patrones laxos de `readfig` en zh (`图.*说明`) no tienen equivalente
        # en es-MX y casan por coincidencia («完整图景……说明»). Si el original no
        # trae el marcador estricto (读图), la falta de lectura de figuras es suya.
        from note_language import ZH
        if not ZH.count("readfig_strict", zh_text):
            inherited[READFIG_ERROR] = ""
        found += [(key, line) for key, line in coverage_errors(es).items() if key not in inherited]
        if compile_ and "\\documentclass" in es_text:
            # Un capítulo incluido no compila solo: lo compila la nota que lo incluye.
            found += compile_signal(es)
        note_rows = [{"note": rel(es, root), "signal": s, "detail": d} for s, d in found]
        cached.write_text(json.dumps(note_rows, ensure_ascii=False), encoding="utf-8")
        rows += note_rows
    return rows, hits


READFIG_ERROR = "coverage:figures-present-but-no-readfig-explanation"


def coverage_errors(note: Path) -> dict[str, str]:
    result = subprocess.run([sys.executable, str(HERE / "check_note_coverage.py"), str(note)],
                            capture_output=True, text=True)
    return {f"coverage:{l.split()[1].split('=')[0]}": l
            for l in result.stdout.splitlines() if l.startswith("ERROR ")}


def load_lexicons():
    import check_prose_vocabulary as prose
    es_lex, en_lex = prose.load_lexicons()
    keep, rejected = prose.load_glossary(prose.DEFAULT_GLOSSARY)
    forbidden = prose.load_forbidden(prose.DEFAULT_FORBIDDEN) + rejected
    return es_lex, en_lex, prose.load_lemmas(), forbidden, keep, prose.load_baseline(prose.DEFAULT_BASELINE)


def verify_each(notes: list[Path], compile_: bool, root: Path, lexicons) -> tuple[list[dict], int, set[str], dict[str, str]]:
    """Verifica nota por nota: una que falla queda nombrada, no se pierde el lote."""
    rows, hits, done, failed = [], 0, set(), {}
    for note in notes:
        try:
            note_rows, note_hits = verify_notes([note], compile_, root, lexicons)
        except Exception as error:  # noqa: BLE001 — cualquier falla deja la nota sin veredicto
            failed[rel(note, root)] = f"{type(error).__name__}: {error}"[:160]
            continue
        rows += note_rows
        hits += note_hits
        done.add(rel(note, root))
    return rows, hits, done, failed


def incomplete_rows(notes: list[Path], root: Path, done: set[str], failed: dict[str, str]) -> list[dict]:
    """Toda nota sin veredicto es una señal: nunca cuenta como limpia.

    cs329a, iteración 02: un `verify-one` murió y «sin filas» se leyó como
    «sin señales». El veredicto se cruza contra la lista pedida, nota por nota.
    """
    return [{"note": rel(n, root), "signal": "verify:incomplete",
             "detail": failed.get(rel(n, root), "el verificador no reportó esta nota")}
            for n in notes if rel(n, root) not in done]


def run_verify(notes: list[Path], compile_: bool, jobs: int, root: Path) -> tuple[list[dict], int]:
    """Una nota: en este proceso. Varias: repartidas con GNU Parallel."""
    if len(notes) <= 1 or not shutil.which("parallel"):
        rows, hits, done, failed = verify_each(notes, compile_, root, load_lexicons())
        return rows + incomplete_rows(notes, root, done, failed), hits
    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "notes.txt"
        listing.write_text("\n".join(str(n) for n in notes) + "\n", encoding="utf-8")
        cmd = ["parallel", "--will-cite", "-j", str(jobs), "-n", "10", "-a", str(listing),
               sys.executable, str(HERE / "translation_loop.py"), "verify-one", "--root", str(root)]
        if compile_:
            cmd.append("--compile")
        result = subprocess.run(cmd + ["{}"], capture_output=True, text=True)
    rows, done, failed = [], set(), {}
    for line in result.stdout.splitlines():
        if line.startswith("{"):
            rows.append(json.loads(line))
    for line in result.stderr.splitlines():
        if line.startswith("verified "):
            done.add(line[len("verified "):])
        elif line.startswith("failed "):
            note, _sep, reason = line[len("failed "):].partition("\t")
            failed[note] = reason
    hits = sum(int(l.split()[1]) for l in result.stderr.splitlines() if l.startswith("hits "))
    return rows + incomplete_rows(notes, root, done, failed), hits


def cmd_verify_one(args) -> int:
    rows, hits, done, failed = verify_each([Path(n).resolve() for n in args.notes], args.compile, args.root,
                                           load_lexicons())
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    for note in sorted(done):
        print(f"verified {note}", file=sys.stderr)
    for note, reason in failed.items():
        print(f"failed {note}\t{reason}", file=sys.stderr)
    print(f"hits {hits}", file=sys.stderr)
    return 1 if failed else 0


def cmd_verify(args) -> int:
    root = Path.cwd()
    notes = [Path(n).resolve() for n in args.notes]
    rows, hits = run_verify(notes, args.compile, args.jobs, root)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"cache: {hits} de {len(notes)} nota(s)", file=sys.stderr)
    print(f"verify: {len(rows)} senal(es) en {len(notes)} nota(s) -> {args.out}")
    incomplete = [r["note"] for r in rows if r["signal"] == "verify:incomplete"]
    if incomplete:
        print(f"verify: verificación incompleta en {len(incomplete)} nota(s): {', '.join(incomplete[:5])}",
              file=sys.stderr)
        return 2
    return 1 if rows else 0


# --- cycle ----------------------------------------------------------------

REGISTRY_HEADER = ["batch", "iteration", "started", "notes", "units", "translated", "signals", "exit"]


def batch_bench(batch: str) -> Path:
    """El banco estable de un lote: el mismo en cada iteración, nunca uno por ejecución."""
    return Path.cwd() / ".claude" / "workbench" / "translation" / batch


def record_iteration(registry: Path, row: dict) -> None:
    """Agrega una fila al registro de lotes; nunca reescribe las anteriores."""
    if not registry.is_file():
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text("\t".join(REGISTRY_HEADER) + "\n", encoding="utf-8")
    with registry.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(str(row[k]) for k in REGISTRY_HEADER) + "\n")


def cmd_cycle(args) -> int:
    """prepare → translate → assemble → verify (+ usage), como una iteración del lote.

    El plan (secciones 6 y 7) pide el registro de cada iteración en el banco del
    lote, versionado. El banco es estable por lote
    (`.claude/workbench/translation/<lote>/`), cada ejecución escribe en
    `iterations/NN/` sin tocar las anteriores y agrega una fila a
    `translation/batches.tsv`.

    Si un fragmento no vuelve con marcadores, `assemble` no escribe esa nota:
    una nota a medias nunca queda junto al original. Esa es la guarda; el
    código de salida de `translate` no agrega nada (anulado, nada cambia).
    """
    ns = argparse.Namespace
    bench = args.bench or batch_bench(args.batch)
    batch = args.batch or bench.name
    iterations = bench / "iterations"
    number = f"{len([d for d in iterations.glob('[0-9][0-9]') if d.is_dir()]) + 1:02d}"
    here = iterations / number
    here.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    before = set(bench.glob("translate/*"))
    if cmd_prepare(ns(bench=bench, notes=args.notes)):
        return 1
    pending = len(pending_units(bench))
    translated = cmd_translate(ns(bench=bench, model=args.model, width=args.width, memfree=args.memfree,
                                  timeout=args.timeout, memory=args.memory))
    cmd_usage(ns(bench=bench, runs=sorted(set(bench.glob("translate/*")) - before), out=here / "usage.tsv"))
    notes = [l.split("\t")[2] for l in (bench / "notes.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    signals = here / "signals.jsonl"
    if translated == 5:
        signals.write_text("", encoding="utf-8")
        code, count = 5, "limite"
    elif cmd_assemble(ns(bench=bench)):
        signals.write_text("", encoding="utf-8")
        code, count = 1, "sin-ensamblar"
    else:
        code = cmd_verify(ns(out=signals, compile=args.compile, jobs=args.jobs, notes=notes))
        count = len([l for l in signals.read_text(encoding="utf-8").splitlines() if l.strip()])
    units = len([l for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip()])
    # El puntero al lote en curso: versionado, lo escribe el ciclo y no la shell.
    pointer = Path.cwd() / ".claude" / "workbench" / ".last-bank"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(rel(bench.resolve(), Path.cwd().resolve()) + "\n", encoding="utf-8")
    record_iteration(bench.parent / "batches.tsv", {
        "batch": batch, "iteration": number, "started": started, "notes": len(notes), "units": units,
        "translated": pending, "signals": count, "exit": code})
    return code


# --- plan -------------------------------------------------------------------

SKIPPED_DIRS = {".git", ".venv", ".claude", "node_modules", ".web-build", ".web-build-es-mx"}


def batch_name(course: str) -> str:
    """`talks/lab/sp25` → `talks__lab__sp25`: el nombre del banco del lote."""
    return course.replace("/", "__") if course not in ("", ".") else "raiz"


def cmd_plan(args) -> int:
    """Fase 3 del plan: un lote por curso, del más pequeño al más grande.

    El curso de una nota es el directorio que contiene al de la nota
    (`cs329a/lecture01/…` → `cs329a`). El plan se escribe versionado; el
    tamaño es el de los originales zh, que es lo que el traductor recibe.
    """
    root = Path.cwd()
    courses: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*-notes.tex")):
        parts = path.relative_to(root).parts
        if path.name.endswith(".es-mx.tex") or SKIPPED_DIRS & set(parts):
            continue
        # El curso es el directorio que contiene al de la nota; una nota a un solo
        # nivel (`self-evolving-agents-2026/…`) es su propio curso, no «.».
        course = str(Path(*parts[:-2])) if len(parts) > 2 else (parts[0] if len(parts) == 2 else ".")
        courses.setdefault(course, []).append(path)
    sized = sorted(((sum(p.stat().st_size for p in ps), c, ps) for c, ps in courses.items()), key=lambda t: (t[0], t[1]))
    lines = ["\t".join(["order", "batch", "bytes", "notes", "paths"])]
    for order, (size, course, paths) in enumerate(sized, 1):
        lines.append("\t".join([str(order), batch_name(course), str(size), str(len(paths)),
                                 " ".join(rel(p, root) for p in paths)]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"plan: {len(sized)} lote(s), {sum(len(t[2]) for t in sized)} nota(s) -> {args.out}", file=sys.stderr)
    return 0


# --- triage -------------------------------------------------------------------

ROUTE_ORDER = {"deterministic": 0, "shared": 1, "local": 2}


def latest_signals(root: Path) -> list[dict]:
    """Las señales de la última iteración de cada lote."""
    rows = []
    for bench in sorted((root / ".claude" / "workbench" / "translation").glob("*/iterations")):
        last = sorted(d for d in bench.glob("[0-9][0-9]") if d.is_dir())
        if last and (last[-1] / "signals.jsonl").is_file():
            rows += [json.loads(l) for l in (last[-1] / "signals.jsonl").read_text(encoding="utf-8").splitlines()
                     if l.strip()]
    return rows


GLYPH = re.compile(r"There is no (?P<char>\S+) \(U\+(?P<code>[0-9A-F]+)\)")


def cause_key(row: dict) -> str:
    """La causa de una señal, que es lo que se agrupa (plan v3).

    Una señal de prosa ya lleva su texto (`prose:english:pools`). Las genéricas
    (`compile:error`, `compile:missing-glyph`, `coverage:…`) juntan causas
    distintas bajo un nombre: «（» en una nota y «张» en otra son dos causas
    (memoria mecánica y fuente CJK), y agruparlas por nombre las volvía una
    causa compartida falsa. Todos los Han son una causa: ninguno tiene glifo.
    """
    signal, detail = row["signal"], row.get("detail") or ""
    if signal.count(":") >= 2:
        return signal
    if signal == "compile:missing-glyph":
        glyph = GLYPH.search(detail)
        if glyph:
            return f"{signal}:han" if HAN.fullmatch(glyph.group("char")) else f"{signal}:U+{glyph.group('code')}"
    if signal == "parity:residual-han":
        # «Ungrounded 不着边际» en dos notas es una causa; «推理» y «构建模型», dos.
        han = re.search(r"[\u4e00-\u9fff]+", detail.partition("primera:")[2])
        return f"{signal}:{han.group(0)}" if han else signal
    if signal == "compile:error":
        message, _sep, context = detail.partition(" | ")
        command = re.search(r"(\\[A-Za-z]+)\s*$", context)
        return f"{signal}:{message.lstrip('! ').strip()}" + (f":{command.group(1)}" if command else "")
    return signal


def classify(root: Path, memory: Path) -> dict[str, tuple[str, list[str]]]:
    """Ruta de cada señal según dónde vive su causa (plan v3).

    - determinista: un arreglo `mechanical` de la memoria la cubre;
    - compartida: la misma señal en dos notas o más, de cualquier lote; se
      decide una vez (glosario, plantilla, verificador, preámbulo);
    - local: el resto; se retraduce su fragmento.
    """
    # Un arreglo mecánico cubre una señal solo si su texto está en la nota, igual
    # que en el barrido: por el nombre de la señal, la entrada de `title=#1`
    # (clave `compile:error`) volvía determinista todo error de compilación.
    mechanical = [(e["senal_del_verificador"], e["fix_generico"]["buscar"]) for e in read_jsonl(memory)
                  if isinstance(e.get("fix_generico"), dict) and e["fix_generico"].get("tipo") == "mechanical"]
    texts: dict[str, str] = {}

    def note_text(note: str) -> str:
        if note not in texts:
            path = root / note
            texts[note] = path.read_text(encoding="utf-8") if path.is_file() else ""
        return texts[note]

    notes: dict[str, set[str]] = {}
    names: dict[str, str] = {}
    for row in latest_signals(root):
        key = cause_key(row)
        notes.setdefault(key, set()).add(row["note"])
        names[key] = row["signal"]
    out = {}
    for key, where in notes.items():
        # La memoria nombra la señal, no la causa: se compara con el nombre base.
        if any(fnmatch.fnmatchcase(names[key], pattern) and any(text in note_text(n) for n in where)
               for pattern, text in mechanical):
            route = "deterministic"
        elif len(where) > 1:
            route = "shared"
        else:
            route = "local"
        out[key] = (route, sorted(where))
    return out


def cmd_triage(args) -> int:
    root = Path.cwd()
    routes = classify(root, args.memory)
    ordered = sorted(routes.items(), key=lambda kv: (ROUTE_ORDER[kv[1][0]], -len(kv[1][1]), kv[0]))
    out = root / ".claude" / "workbench" / "translation" / "triage.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("route\tsignal\tnotes\tpaths\n" + "".join(
        f"{route}\t{signal}\t{len(where)}\t{' '.join(where)}\n" for signal, (route, where) in ordered), encoding="utf-8")
    counts = collections.Counter(route for route, _w in routes.values())
    print(f"triage: {counts['deterministic']} determinista(s), {counts['shared']} compartida(s), "
          f"{counts['local']} local(es) -> {out}", file=sys.stderr)
    return 0


DECISIONS_HEADER = ("decision", "started", "before", "after", "resolved", "introduced", "net", "incomplete")


def translated_notes(root: Path) -> list[Path]:
    """Toda nota o capítulo es-MX del corpus, podando lo que no es corpus."""
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIPPED_DIRS)
        found += [Path(base, f).resolve() for f in files if f.endswith(".es-mx.tex")]
    return sorted(found)


def cmd_measure(args) -> int:
    """El efecto neto de una decisión de ruta 2, antes de tomar la siguiente.

    Plan v3, paso 3: una causa compartida a la vez. Se verifica todo el corpus
    traducido —una regla del glosario puede introducir señales en notas que
    estaban limpias— y se compara, por (nota, causa), con la medición anterior,
    que tiene el mismo alcance. Sin medición anterior no hay neto: la primera es
    la línea base. (Contra la última iteración de cada lote se mezclaban
    alcances: una iteración sin ensamblar deja 0 señales y los preámbulos
    compartidos no están en ninguna.) `decisions.tsv` es
    de solo agregar; cada medición queda en `measures/NNN-<ISO>.jsonl`. Sale
    con 4 si el neto es negativo y con 2 si la verificación quedó incompleta.
    """
    root = Path.cwd()
    translation = root / ".claude" / "workbench" / "translation"
    measures = translation / "measures"
    measures.mkdir(parents=True, exist_ok=True)
    previous = sorted(measures.glob("*.jsonl"))
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows, _hits = run_verify(translated_notes(root), args.compile, args.jobs, root)
    snapshot = measures / f"{len(previous) + 1:03d}-{started}.jsonl"
    snapshot.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    table = translation / "decisions.tsv"
    if not table.is_file():
        table.write_text("\t".join(DECISIONS_HEADER) + "\n", encoding="utf-8")
    incomplete = sum(1 for r in rows if r["signal"] == "verify:incomplete")
    if not previous:
        with table.open("a", encoding="utf-8") as handle:
            handle.write("\t".join(str(v) for v in (args.decision, started, "", len(rows), "", "", "", incomplete)) + "\n")
        print(f"measure: línea base registrada con {len(rows)} señal(es); la siguiente decisión se mide contra ella "
              f"-> {table}", file=sys.stderr)
        return 2 if incomplete else 0
    before_rows = read_jsonl(previous[-1])
    before = {(r["note"], cause_key(r)) for r in before_rows}
    after = {(r["note"], cause_key(r)) for r in rows}
    resolved, introduced = before - after, after - before
    values = (args.decision, started, len(before), len(after), len(resolved), len(introduced),
              len(resolved) - len(introduced), incomplete)
    with table.open("a", encoding="utf-8") as handle:
        handle.write("\t".join(str(v) for v in values) + "\n")
    for note, key in sorted(introduced):
        print(f"measure: introducida {key} en {note}", file=sys.stderr)
    print(f"measure: {args.decision}: {len(resolved)} resuelta(s), {len(introduced)} introducida(s), "
          f"neto {len(resolved) - len(introduced)} -> {table}", file=sys.stderr)
    if incomplete:
        return 2
    if len(introduced) > len(resolved):
        # Plan v3: cada decisión se mide antes de la siguiente; si introduce más
        # de lo que resuelve, se revierte, y el código de salida lo exige.
        print(f"measure: neto negativo; la decisión «{args.decision}» se revierte antes de la siguiente",
              file=sys.stderr)
        return 4
    return 0


# --- retranslate ------------------------------------------------------------

# Las señales que llevan el texto que las produjo, y cómo buscarlo en un fragmento.
LOCATABLE = ("prose:english:", "prose:spanglish:", "prose:unaccented:", "prose:invented:", "prose:forbidden:")


def cmd_retranslate(args) -> int:
    """Devuelve a pendientes los fragmentos que llevan una señal de la última iteración.

    Paso 3 del plan: corregida la causa raíz (plantilla, glosario), se
    retraducen los fragmentos afectados y ningún otro. Una señal sin texto que
    buscar (cobertura, compilación, paridad) se lista como `manual`. La lista
    queda en `iterations/NN/retranslate.tsv` de la iteración que la produjo.
    """
    bench = args.bench or batch_bench(args.batch)
    iterations = sorted(d for d in (bench / "iterations").glob("[0-9][0-9]") if d.is_dir())
    if not iterations:
        print(f"retranslate: {bench} no tiene iteraciones", file=sys.stderr)
        return 2
    here = iterations[-1]
    rows = [json.loads(l) for l in (here / "signals.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    units = [l.split("\t") for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    notes = [l.split("\t") for l in (bench / "notes.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    root = Path.cwd()
    note_ids = {rel(Path(target), root): note_id for _zh, note_id, target, *_base in notes}
    out, marked = [], set()
    routes = classify(root, args.memory)
    for row in rows:
        signal, note_id = row["signal"], note_ids.get(row["note"])
        route = routes.get(cause_key(row), ("local", []))[0]
        if route != "local":
            # Rutas 1 y 2 del plan v3: el arreglo no es retraducir este fragmento.
            out.append((signal, row["note"], "", route))
            continue
        prefix = next((p for p in LOCATABLE if signal.startswith(p)), None)
        command = re.search(r"(\\[A-Za-z]+)\s*$", row.get("detail", "")) if signal == "compile:error" else None
        if (prefix is None and command is None) or note_id is None:
            out.append((signal, row["note"], "", "manual"))
            continue
        if command is not None:
            # El comando que la compilación no conoce, tal como lo escribe el fragmento.
            pattern = re.compile(re.escape(command.group(1)) + r"(?![A-Za-z])")
        else:
            text = signal[len(prefix):]
            # La frontera es de letra, no de palabra con guion: el verificador
            # parte «hard-coding» en `hard` y `coding` (cs329a, iteración 03).
            pattern = re.compile(rf"(?<![^\W\d_]){re.escape(text)}(?![^\W\d_])", re.I)
        found = False
        for unit in (u for u in units if u[1] == note_id):
            es = Path(unit[4])
            if es.is_file() and pattern.search(es.read_text(encoding="utf-8")):
                out.append((signal, row["note"], es.name, "retranslate"))
                marked.add(es)
                found = True
        if not found:
            # Una señal que no se encuentra va a juicio: nunca desaparece de la lista.
            out.append((signal, row["note"], "", "manual"))
    # Auditoría de estructura, con o sin señal: un fragmento ya escrito que no
    # conserva los entornos de su original vuelve a pendientes.
    for unit in units:
        zh, es = Path(unit[3]), Path(unit[4])
        if es.is_file() and es not in marked:
            problem = structure_problem(zh.read_text(encoding="utf-8"), es.read_text(encoding="utf-8"))
            if problem:
                note = next((n for n, i in note_ids.items() if i == unit[1]), unit[1])
                out.append((f"structure:{problem}", note, es.name, "retranslate"))
                marked.add(es)
    for es in marked:
        es.unlink()
    (here / "retranslate.tsv").write_text(
        "signal\tnote\tchunk\taction\n" + "".join("\t".join(r) + "\n" for r in out), encoding="utf-8")
    manual = sum(1 for r in out if r[3] == "manual")
    print(f"retranslate: {len(marked)} fragmento(s) a pendientes; {manual} señal(es) para juicio -> {here / 'retranslate.tsv'}",
          file=sys.stderr)
    return 0


# --- advance ------------------------------------------------------------------

def batch_notes(plan: Path, batch: str) -> list[str]:
    """Las notas de un lote según el plan versionado."""
    for line in plan.read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) >= 5 and fields[1] == batch:
            return fields[4].split(" ")
    return []


def cmd_advance(args) -> int:
    """Itera las rutas 1 y 3 de un lote y se detiene cuando hace falta juicio.

    Cada vuelta: `cycle`; si hay una señal compartida (ruta 2) se detiene y la
    nombra, porque se decide una vez y no se retraduce nota por nota; si no,
    `sweep` (ruta 1) y `retranslate` (ruta 3). Sale con 0 si el lote queda
    limpio, 2 si la verificación quedó incompleta y 3 si hace falta juicio:
    una causa compartida, señales que no se pueden localizar o el tope de
    iteraciones.
    """
    ns = argparse.Namespace
    root = Path.cwd()
    notes = batch_notes(args.plan, args.batch)
    if not notes:
        print(f"advance: el lote {args.batch} no está en {args.plan}", file=sys.stderr)
        return 2
    bench = batch_bench(args.batch)
    # Los pares (nota, causa) que la vuelta anterior mandó a retraducir.
    retranslated: set[tuple[str, str]] = set()
    for _round in range(args.max_iterations):
        code = cmd_cycle(ns(batch=args.batch, bench=None, model=args.model, width=args.width, memfree=args.memfree,
                            timeout=args.timeout, memory=args.memory, compile=args.compile, jobs=args.jobs,
                            notes=notes))
        if code in (0, 2, 5):
            return code
        last = sorted(d for d in (bench / "iterations").glob("[0-9][0-9]") if d.is_dir())[-1]
        if pending_units(bench):
            # Fragmentos rechazados al recibirlos (sin marcadores, estructura rota):
            # son la siguiente vuelta, no un juicio (ola 1: siete lotes paraban aquí).
            continue
        rows_now = [json.loads(l) for l in (last / "signals.jsonl").read_text(encoding="utf-8").splitlines()
                    if l.strip()]
        signals = {cause_key(r) for r in rows_now}
        routes = classify(root, args.memory)
        shared = sorted(s for s in signals if routes.get(s, ("local",))[0] == "shared")
        if shared:
            print(f"advance: {len(shared)} causa(s) compartida(s); se deciden una vez (hace falta juicio): "
                  + ", ".join(shared[:10]), file=sys.stderr)
            return 3
        # Una señal que vuelve igual tras retraducir su fragmento no cede a
        # retraducir: «resolubilidad» e «internalizar» sobrevivieron a tres
        # retraducciones y sólo cedieron a una fila del glosario. Se detiene ya,
        # no en el tope, y la nombra para decidirla una vez.
        persistent = sorted({f"{cause_key(r)} en {r['note']}" for r in rows_now
                             if (r["note"], cause_key(r)) in retranslated})
        if persistent:
            print(f"advance: {len(persistent)} señal(es) sobrevive(n) a la retraducción de su fragmento; hace "
                  "falta juicio (glosario o regla): " + ", ".join(persistent[:10]), file=sys.stderr)
            return 3
        # En una ola (`translate_wave.sh`) varios lotes corren a la vez: el barrido
        # reescribe la memoria, así que corre una sola vez al final de la ola.
        if not args.no_sweep and any(routes.get(s, ("local",))[0] == "deterministic" for s in signals):
            cmd_sweep(ns(bench=bench, iteration=int(last.name), memory=args.memory, jobs=args.jobs))
        cmd_retranslate(ns(batch=args.batch, bench=None, memory=args.memory))
        listed = (last / "retranslate.tsv").read_text(encoding="utf-8").splitlines()[1:]
        marked = [l for l in listed if l.endswith("\tretranslate")]
        pairs = {(l.split("\t")[0], l.split("\t")[1]) for l in marked}
        retranslated = {(r["note"], cause_key(r)) for r in rows_now if (r["signal"], r["note"]) in pairs}
        if not marked and not any(routes.get(s, ("local",))[0] == "deterministic" for s in signals):
            print(f"advance: {len(listed)} señal(es) sin fragmento que retraducir; hace falta juicio", file=sys.stderr)
            return 3
    print(f"advance: tope de {args.max_iterations} iteraciones con señales abiertas; hace falta juicio",
          file=sys.stderr)
    return 3


# --- sweep ----------------------------------------------------------------

def needs_fix(text: str, fix: dict) -> bool:
    """¿Aplica el arreglo mecánico a este texto, sin aplicarlo dos veces?

    Un reemplazo que contiene lo buscado (llevar xeCJK a las notas ya
    traducidas: «…{spanish}» → «…{spanish}\\n\\usepackage{xeCJK}») se aplicaría
    de nuevo en cada ola; si el texto ya trae el reemplazo, no se toca.
    """
    if fix["buscar"] not in text:
        return False
    return not (fix["buscar"] in fix["reemplazar"] and fix["reemplazar"] in text)


def cmd_sweep(args) -> int:
    root = Path.cwd()
    # Las notas del producto, nunca las copias de evidencia bajo `.claude/`: el
    # barrido corrigió una en `.claude/workbench/` y contaba 10 notas en un lote de 9.
    # Y todo lo traducido, no sólo `*-notes`: en la ola 3 el respaldo CJK no
    # llegó a cuatro preámbulos compartidos ni a dos plantillas, que `measure`
    # sí verifica. `translated_notes` es el mismo recorrido para los dos.
    notes = translated_notes(root)
    rows, _ = run_verify(notes, False, args.jobs, root)
    memory = read_jsonl(args.memory)
    chunks = sorted((root / ".claude" / "workbench" / "translation").glob("*/chunks/*/*.es.tex"))
    chunks += [c for c in sorted(args.bench.glob("chunks/*/*.es.tex")) if c not in chunks]
    sweep_log = args.bench / "sweep.jsonl"
    retranslate = []
    with sweep_log.open("a", encoding="utf-8") as log:
        for entry in memory:
            fix = entry["fix_generico"]
            applied = 0
            if fix.get("tipo") == "mechanical":
                # Ruta 1 (determinista, plan v3): por texto y no por señal (la del
                # glifo solo sale compilando), en la nota y en sus fragmentos, que
                # son la fuente de verdad: el siguiente ensamblado no la deshace.
                hit = sorted(rel(n, root) for n in notes if needs_fix(n.read_text(encoding="utf-8"), fix))
                for path in [root / n for n in hit] + chunks:
                    text = path.read_text(encoding="utf-8")
                    if needs_fix(text, fix):
                        path.write_text(text.replace(fix["buscar"], fix["reemplazar"]), encoding="utf-8")
                applied = len(hit)
            else:
                hit = sorted({r["note"] for r in rows if fnmatch.fnmatchcase(r["signal"], entry["senal_del_verificador"])})
                retranslate += [{"note": note, "senal": entry["senal_del_verificador"], "tipo": fix.get("tipo")}
                                for note in hit]
            for note in hit:
                if note not in entry["archivos_donde_ya_se_aplico"]:
                    entry["archivos_donde_ya_se_aplico"].append(note)
            log.write(json.dumps({"iteration": args.iteration, "senal_del_verificador": entry["senal_del_verificador"],
                                  "notas_revisadas": len(notes), "instancias": len(hit), "aplicadas": applied},
                                 ensure_ascii=False) + "\n")
    args.memory.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in memory), encoding="utf-8")
    if retranslate:
        with (args.bench / "retranslate.jsonl").open("a", encoding="utf-8") as handle:
            handle.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in retranslate)
    print(f"sweep: iteracion {args.iteration}, {len(memory)} patron(es) sobre {len(notes)} nota(s); "
          f"{len(retranslate)} instancia(s) para retraducir")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--bench", type=Path, required=True)
    p.add_argument("notes", nargs="+"); p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("prompt"); p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.add_argument("--out", type=Path, required=True); p.set_defaults(func=cmd_prompt)
    p = sub.add_parser("translate"); p.add_argument("--bench", type=Path, required=True)
    p.add_argument("--model", required=True); p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--memfree", default=DEFAULT_MEMFREE)
    p.add_argument("--timeout", type=int, default=900); p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.set_defaults(func=cmd_translate)
    p = sub.add_parser("usage"); p.add_argument("--bench", type=Path, required=True); p.set_defaults(func=cmd_usage)
    p = sub.add_parser("assemble"); p.add_argument("--bench", type=Path, required=True); p.set_defaults(func=cmd_assemble)
    p = sub.add_parser("plan"); p.add_argument("--out", type=Path, required=True); p.set_defaults(func=cmd_plan)
    p = sub.add_parser("advance"); p.add_argument("--batch", required=True)
    p.add_argument("--plan", type=Path, default=Path(".claude/workbench/translation/plan.tsv"))
    p.add_argument("--model", required=True); p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--memfree", default=DEFAULT_MEMFREE); p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY); p.add_argument("--compile", action="store_true")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    p.add_argument("--max-iterations", type=int, default=4); p.add_argument("--no-sweep", action="store_true")
    p.set_defaults(func=cmd_advance)
    p = sub.add_parser("triage"); p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.set_defaults(func=cmd_triage)
    p = sub.add_parser("measure"); p.add_argument("--decision", required=True)
    p.add_argument("--compile", action="store_true")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 2); p.set_defaults(func=cmd_measure)
    p = sub.add_parser("retranslate"); p.add_argument("--batch", default=None)
    p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.add_argument("--bench", type=Path, default=None); p.set_defaults(func=cmd_retranslate)
    p = sub.add_parser("cycle"); p.add_argument("--batch", default=None)
    p.add_argument("--bench", type=Path, default=None, help="por defecto .claude/workbench/translation/<lote>")
    p.add_argument("--model", required=True); p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--memfree", default=DEFAULT_MEMFREE); p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY); p.add_argument("--compile", action="store_true")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    p.add_argument("notes", nargs="+"); p.set_defaults(func=cmd_cycle)
    p = sub.add_parser("verify"); p.add_argument("--out", type=Path, required=True)
    p.add_argument("--compile", action="store_true"); p.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    p.add_argument("notes", nargs="+"); p.set_defaults(func=cmd_verify)
    p = sub.add_parser("verify-one"); p.add_argument("--root", type=Path, required=True)
    p.add_argument("--compile", action="store_true"); p.add_argument("notes", nargs="+"); p.set_defaults(func=cmd_verify_one)
    p = sub.add_parser("sweep"); p.add_argument("--bench", type=Path, required=True)
    p.add_argument("--iteration", type=int, required=True); p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 2); p.set_defaults(func=cmd_sweep)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
