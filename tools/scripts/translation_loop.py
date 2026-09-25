#!/usr/bin/env python3
"""El motor del ciclo de traduccion es-MX (`docs/ES_MX_TRANSLATION_PLAN.md`).

    translation_loop.py prepare  --bench B <nota.tex>...
    translation_loop.py prompt   [--memory M] --out P.md
    translation_loop.py translate --bench B --model <id completo> [--width N] [--memfree TAM] [--timeout S]
    translation_loop.py usage    --bench B
    translation_loop.py cycle    --batch L --model <id> [--compile] <nota.tex>...
    translation_loop.py assemble --bench B
    translation_loop.py verify   --out S.jsonl [--compile] [--jobs N] <nota.es-mx.tex>...
    translation_loop.py sweep    --bench B --iteration N [--memory M] [--jobs N]

La unidad del traductor es el FRAGMENTO: el cuerpo de la nota partido por
`\\section` (y por `\\subsection` si una seccion es larga). Asi una nota grande
no depende de lo que una conversacion alcanza a escribir de una vez, y solo se
retraduce el fragmento que falla.

El traductor es `headless-pool` de THYROX via `tools/thyrox/run` (un `claude -p`
por fragmento, repartidos con GNU Parallel); `TRANSLATION_RUNNER` lo sustituye
en las pruebas. La verificacion reparte las notas con GNU Parallel y guarda
cada veredicto en `$THYROX_CACHE_DIR/translation/`, con clave en el contenido
de la nota zh, la es-MX y los verificadores.
"""
from __future__ import annotations

import argparse
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
CHUNK_LIMIT = 12000  # caracteres; una seccion mas larga se parte por \subsection
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


def map_inputs(text: str) -> str:
    return re.sub(r"\\(input|include)\{([^}]+?)(?<!\.es-mx)(\.tex)?\}",
                  lambda m: f"\\{m.group(1)}{{{m.group(2)}.es-mx.tex}}", text)


def split_body(body: str) -> list[str]:
    """Fragmentos: lo anterior a la primera seccion, y una por seccion."""
    parts = re.split(r"(?m)^(?=\\section\*?\{)", body)
    chunks: list[str] = []
    for part in parts:
        if len(part) <= CHUNK_LIMIT:
            chunks.append(part)
            continue
        chunks.extend(p for p in re.split(r"(?m)^(?=\\subsection\*?\{)", part) if p)
    return chunks


# --- prepare --------------------------------------------------------------

def cmd_prepare(args) -> int:
    from localize_preamble import localize
    root = Path.cwd()
    bench = args.bench
    (bench / "chunks").mkdir(parents=True, exist_ok=True)
    units, notes = [], []
    for zh in args.notes:
        zh = Path(zh).resolve()
        note_id = rel(zh, root)[:-len(".tex")].replace("/", "__")
        text = map_inputs(localize(zh.read_text(encoding="utf-8")))
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
        if HAN.search(COMMENT_LINE.sub("", head)):
            # Lo que el script no localiza del preambulo (`\notetitle`, que es
            # prosa y va en la portada) se traduce como una unidad mas: la
            # fuente latina no tiene esos glifos y XeLaTeX los omitiria en silencio.
            (out / "head.zh.tex").write_text(head, encoding="utf-8")
            units.append("\t".join([rel(zh, root), note_id, "head", str(out / "head.zh.tex"), str(out / "head.es.tex")]))
        for k, chunk in enumerate(split_body(body)):
            zh_chunk = out / f"{k:03d}.zh.tex"
            zh_chunk.write_text(chunk, encoding="utf-8")
            units.append("\t".join([rel(zh, root), note_id, f"{k:03d}", str(zh_chunk), str(out / f"{k:03d}.es.tex")]))
        notes.append("\t".join([rel(zh, root), note_id, str(es_path(zh))]))
    (bench / "units.tsv").write_text("\n".join(units) + "\n", encoding="utf-8")
    (bench / "notes.tsv").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print(f"prepare: {len(notes)} nota(s), {len(units)} fragmento(s) en {bench}")
    return 0


# --- prompt ---------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_prompt(memory: Path) -> str:
    import csv
    from note_language import ES_MX, ZH
    parts = [PROMPT_TEMPLATE.read_text(encoding="utf-8").rstrip(), "", "## Glosario (obligatorio)", "",
             "| Término | Decisión | Forma es-MX | Significado | Formas prohibidas |", "|---|---|---|---|---|"]
    with (LANG_DIR / "glossary.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            parts.append(f"| {row['term_en']} | {row['decision']} | {row.get('es_mx') or '—'} | "
                         f"{row.get('meaning') or ''} | {row.get('rejected') or '—'} |")
    parts += ["", "## Etiquetas de estructura (se traducen siempre así)", ""]
    parts += [f"- `{zh}` → `{es}`" for zh, es in [
        (ZH.section_summary_title, ES_MX.section_summary_title),
        (ZH.final_section_title, ES_MX.final_section_title),
        ("拓展阅读", "Lecturas adicionales"), ("读图", "Lectura de la figura"),
        ("背景概念", "Concepto previo"), ("术语表", "Glosario"), ("术语消化", "Términos clave"),
        ("课堂提示", "Nota de clase"), ("老师强调", "el docente enfatiza"), ("来源", "Fuente")]]
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
# de headless-pool, THYROX bfb4eb15): no lanza un item bajo la cota y reencola
# el mas joven si la memoria baja de la mitad. 3G deja lugar a un `tsc` de 2 GB
# en paralelo. La anchura NO se deriva de la carga —la carga a un minuto mide a
# los otros procesos, no al pool—: solo acota la concurrencia contra la API,
# cuyos limites de tasa no se ven desde el contenedor. 10 es lo que el piloto
# corrio sin un 429; si aparece uno, se baja con `--width`.
DEFAULT_MEMFREE = "3G"
DEFAULT_WIDTH = 10
BEGIN_MARK, END_MARK = "<<<ES", "ES>>>"


def extract_translation(result: str) -> str | None:
    """El fragmento traducido que el modelo devuelve entre marcadores."""
    match = re.search(rf"^{re.escape(BEGIN_MARK)}\n(.*?)\n?^{re.escape(END_MARK)}\s*$", result or "", re.M | re.S)
    return match.group(1) + "\n" if match else None


def collect_results(out_dir: Path, targets: dict[str, str]) -> list[str]:
    """Escribe cada fragmento traducido; devuelve los items sin marcadores."""
    missing = []
    index = out_dir / "index.tsv"
    rows = [l.split("\t", 1) for l in index.read_text(encoding="utf-8").splitlines() if l.strip()] if index.is_file() else []
    for n, zh in rows:
        result_file = out_dir / f"{n}.json"
        try:
            result = json.loads(result_file.read_text(encoding="utf-8")).get("result", "")
        except (OSError, ValueError):
            result = ""
        text = extract_translation(result)
        if text is None:
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
    # piloto pago una conversacion entera para oir que no habia nada que traducir.
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
           "--model", args.model, "--tools", "Read", "--width", str(args.width), "--memfree", args.memfree,
           "--timeout", str(args.timeout), "--max-turns", "4", "--cwd", str(Path.cwd())]
    print(f"translate: width={args.width} memfree={args.memfree}", file=sys.stderr)
    code = subprocess.run(cmd, input="".join(f"{row[3]}\n" for row in pending), text=True).returncode
    missing = collect_results(out_dir, {row[3]: row[4] for row in pending})
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
    for _zh, note_id, target in notes:
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
        Path(target).write_text(localized_figures(head + body, Path(target).parent), encoding="utf-8")
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


def fingerprint(compile_: bool) -> str:
    digest = hashlib.sha256(b"compile" if compile_ else b"")
    for name in VERIFIERS:
        digest.update((HERE / name).read_bytes())
    for name in ("glossary.tsv", "prohibited_forms.txt", "prose_vocabulary_baseline.txt"):
        digest.update((LANG_DIR / name).read_bytes())
    return digest.hexdigest()


def compile_signal(es: Path) -> list[tuple[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        for _ in range(2):
            subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", tmp, es.name],
                           cwd=es.parent, capture_output=True, text=True, timeout=600)
        # El PDF solo no basta: con `-halt-on-error` las paginas ya enviadas
        # llegan al PDF aunque despues haya un error (piloto cs329a/lecture01).
        pdf = Path(tmp) / (es.name[:-len(".tex")] + ".pdf")
        log = Path(tmp) / (es.name[:-len(".tex")] + ".log")
        lines = log.read_text(errors="ignore").splitlines() if log.is_file() else []
        first = next((l for l in lines if l.startswith("! ")), None)
        if first is not None or not (pdf.is_file() and pdf.stat().st_size > 0):
            return [("compile:error", (first or "sin PDF")[:160])]
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
            rows += json.loads(cached.read_text(encoding="utf-8"))
            hits += 1
            continue
        zh_text = zh.read_text(encoding="utf-8")
        found = compare(zh_text, es.read_text(encoding="utf-8"), DEFAULT_GLOSSARY)
        # El ingles que la nota zh ya escribe es termino tecnico que se queda
        # (`reward model`, opciones de tcolorbox); solo es defecto el que
        # introdujo la traduccion.
        inherited_english = {w.lower() for w in re.findall(r"[A-Za-z]+", zh_text)}
        for k in prose.scan([es], es_lex, en_lex, forbidden, keep, root, lemmas):
            if k in baseline:
                continue
            if k.startswith("english:"):
                word = k.split(":", 1)[1]
                if word in inherited_english or prose.singular(word) in inherited_english:
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
        # no un defecto de la traduccion: solo sale lo que la traduccion rompio.
        inherited = coverage_errors(zh)
        found += [(key, line) for key, line in coverage_errors(es).items() if key not in inherited]
        if compile_:
            found += compile_signal(es)
        note_rows = [{"note": rel(es, root), "signal": s, "detail": d} for s, d in found]
        cached.write_text(json.dumps(note_rows, ensure_ascii=False), encoding="utf-8")
        rows += note_rows
    return rows, hits


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


def run_verify(notes: list[Path], compile_: bool, jobs: int, root: Path) -> tuple[list[dict], int]:
    """Una nota: en este proceso. Varias: repartidas con GNU Parallel."""
    if len(notes) <= 1 or not shutil.which("parallel"):
        return verify_notes(notes, compile_, root, load_lexicons())
    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "notes.txt"
        listing.write_text("\n".join(str(n) for n in notes) + "\n", encoding="utf-8")
        cmd = ["parallel", "--will-cite", "-j", str(jobs), "-n", "10", "-a", str(listing),
               sys.executable, str(HERE / "translation_loop.py"), "verify-one", "--root", str(root)]
        if compile_:
            cmd.append("--compile")
        result = subprocess.run(cmd + ["{}"], capture_output=True, text=True)
    rows, hits = [], 0
    for line in result.stdout.splitlines():
        if line.startswith("{"):
            rows.append(json.loads(line))
    hits = sum(int(l.split()[1]) for l in result.stderr.splitlines() if l.startswith("hits "))
    return rows, hits


def cmd_verify_one(args) -> int:
    rows, hits = verify_notes([Path(n).resolve() for n in args.notes], args.compile, args.root, load_lexicons())
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    print(f"hits {hits}", file=sys.stderr)
    return 0


def cmd_verify(args) -> int:
    root = Path.cwd()
    notes = [Path(n).resolve() for n in args.notes]
    rows, hits = run_verify(notes, args.compile, args.jobs, root)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"cache: {hits} de {len(notes)} nota(s)", file=sys.stderr)
    print(f"verify: {len(rows)} senal(es) en {len(notes)} nota(s) -> {args.out}")
    return 1 if rows else 0


# --- cycle ----------------------------------------------------------------

REGISTRY_HEADER = ["batch", "iteration", "started", "notes", "units", "translated", "signals", "exit"]


def batch_bench(batch: str) -> Path:
    """El banco estable de un lote: el mismo en cada iteración, nunca uno por corrida."""
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
    (`.claude/workbench/translation/<lote>/`), cada corrida escribe en
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
    cmd_translate(ns(bench=bench, model=args.model, width=args.width, memfree=args.memfree,
                     timeout=args.timeout, memory=args.memory))
    cmd_usage(ns(bench=bench, runs=sorted(set(bench.glob("translate/*")) - before), out=here / "usage.tsv"))
    notes = [l.split("\t")[2] for l in (bench / "notes.tsv").read_text(encoding="utf-8").splitlines() if l.strip()]
    signals = here / "signals.jsonl"
    if cmd_assemble(ns(bench=bench)):
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


# --- sweep ----------------------------------------------------------------

def cmd_sweep(args) -> int:
    root = Path.cwd()
    notes = sorted(p.resolve() for p in root.rglob("*-notes.es-mx.tex") if ".venv" not in p.parts)
    rows, _ = run_verify(notes, False, args.jobs, root)
    memory = read_jsonl(args.memory)
    sweep_log = args.bench / "sweep.jsonl"
    retranslate = []
    with sweep_log.open("a", encoding="utf-8") as log:
        for entry in memory:
            hit = sorted({r["note"] for r in rows if fnmatch.fnmatchcase(r["signal"], entry["senal_del_verificador"])})
            fix = entry["fix_generico"]
            applied = 0
            for note in hit:
                path = root / note
                if fix.get("tipo") == "mechanical":
                    text = path.read_text(encoding="utf-8")
                    new = text.replace(fix["buscar"], fix["reemplazar"])
                    if new != text:
                        path.write_text(new, encoding="utf-8")
                        applied += 1
                else:
                    retranslate.append({"note": note, "senal": entry["senal_del_verificador"], "tipo": fix.get("tipo")})
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
