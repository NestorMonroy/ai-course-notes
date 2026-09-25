#!/usr/bin/env python3
"""El motor del ciclo de traduccion es-MX (`docs/ES_MX_TRANSLATION_PLAN.md`).

    translation_loop.py prepare  --bench B <nota.tex>...
    translation_loop.py prompt   [--memory M] --out P.md
    translation_loop.py translate --bench B --model <id completo> [--width N|auto] [--timeout S]
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


# La anchura del pool se deriva de lo medido, no se fija. Medicion del ejecutor
# (2026-09-25): 26 `claude -p` vivos sumaban 3017 MB de RSS, 116 MB cada uno,
# con carga 0.86 en 4 nucleos. Un `claude -p` pasa casi todo su tiempo
# esperando la API, por eso caben varios por nucleo.
CLAUDE_P_RSS_MB = 116
MEMORY_RESERVE_MB = 2048
PER_CORE = 4
WIDTH_CAP = 16


def auto_width(mem_available_mb: int, load1: float, cpus: int, rss_mb: int = CLAUDE_P_RSS_MB,
               reserve_mb: int = MEMORY_RESERVE_MB, cap: int = WIDTH_CAP) -> int:
    """La anchura que cabe en memoria y en CPU libre, entre 1 y `cap`.

    Ciega a: los limites de tasa de la API, que no se ven desde el contenedor;
    si la API responde 429, se baja `--width` a mano.
    """
    by_memory = (mem_available_mb - reserve_mb) // rss_mb
    by_cpu = int(cpus * PER_CORE * (1 - load1 / cpus))
    return max(1, min(cap, by_memory, by_cpu))


def measured_width() -> tuple[int, str]:
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    available = int(re.search(r"^MemAvailable:\s+(\d+)", meminfo, re.M).group(1)) // 1024
    load1, cpus = os.getloadavg()[0], os.cpu_count() or 1
    width = auto_width(available, load1, cpus)
    return width, f"mem_available_mb={available} load1={load1:.2f} cpus={cpus} rss_mb={CLAUDE_P_RSS_MB}"


def cmd_translate(args) -> int:
    if not FULL_MODEL_ID.match(args.model):
        print(f"translate: `{args.model}` no es un identificador completo (claude-<familia>-<version>); "
              "headless-pool rechaza alias.", file=sys.stderr)
        return 2
    pending = pending_units(args.bench)
    print(f"translate: {len(pending)} fragmento(s) por traducir")
    if not pending:
        return 0
    if args.width == "auto":
        width, measure = measured_width()
    else:
        width, measure = int(args.width), "fijada con --width"
    prompt = args.bench / "prompt.md"
    prompt.write_text(build_prompt(args.memory), encoding="utf-8")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    runner = os.environ.get("TRANSLATION_RUNNER", str(REPO_ROOT / "tools" / "thyrox" / "run"))
    cmd = [runner, "headless-pool", "--prompt", str(prompt), "--out", str(args.bench / "translate" / stamp),
           "--model", args.model, "--tools", "Read,Write", "--width", str(width),
           "--timeout", str(args.timeout), "--max-turns", "8", "--cwd", str(Path.cwd())]
    items = "".join(f"{row[3]}\t{row[4]}\n" for row in pending)
    print(f"translate: width={width} ({measure})", file=sys.stderr)
    return subprocess.run(cmd, input=items, text=True).returncode


# --- assemble -------------------------------------------------------------

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
        head = (args.bench / "chunks" / note_id / "head.tex").read_text(encoding="utf-8")
        body = "".join(Path(r[4]).read_text(encoding="utf-8") for r in sorted(chunks, key=lambda r: r[2]))
        Path(target).write_text(head + body, encoding="utf-8")
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
        pdf = Path(tmp) / (es.name[:-len(".tex")] + ".pdf")
        if pdf.is_file() and pdf.stat().st_size > 0:
            return []
        log = Path(tmp) / (es.name[:-len(".tex")] + ".log")
        first = next((l for l in log.read_text(errors="ignore").splitlines() if l.startswith("! ")), "sin PDF") if log.is_file() else "sin PDF"
        return [("compile:error", first[:160])]


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
        found = compare(zh.read_text(encoding="utf-8"), es.read_text(encoding="utf-8"), DEFAULT_GLOSSARY)
        for k in prose.scan([es], es_lex, en_lex, forbidden, keep, root, lemmas):
            if k in baseline:
                continue
            if k.startswith("english:"):
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
    p.add_argument("--model", required=True); p.add_argument("--width", default="auto")
    p.add_argument("--timeout", type=int, default=900); p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    p.set_defaults(func=cmd_translate)
    p = sub.add_parser("assemble"); p.add_argument("--bench", type=Path, required=True); p.set_defaults(func=cmd_assemble)
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
