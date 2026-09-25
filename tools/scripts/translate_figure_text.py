#!/usr/bin/env python3
"""Traduce a `figure_text.tsv` las cadenas de las figuras conceptuales.

    translate_figure_text.py --missing M.txt --table T.tsv --bench B --model <id completo>
                             [--batch N] [--width N] [--memfree TAM] [--timeout S]

`M.txt` es la salida de `render_zhangxiaojun_concept_figures.py --lang es-mx
--extract`: una cadena por línea. Se agrupan en lotes de `--batch` cadenas y se
traduce cada lote con un `claude -p` de headless-pool (THYROX), con la
plantilla `tools/lang/es-mx/figure_prompt.md`. El modelo devuelve un TSV
`zh<TAB>es` entre `<<<TSV` y `TSV>>>`; solo se aceptan las filas cuyo `zh` es
una cadena que ese lote pidió. Las filas nuevas se agregan a la tabla, que
conserva las que ya tenía. Sale 1 si alguna cadena quedó sin traducción.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT = REPO_ROOT / "tools" / "lang" / "es-mx" / "figure_prompt.md"
FULL_MODEL_ID = re.compile(r"^claude-[a-z]+-\d")
TSV_BLOCK = re.compile(r"^<<<TSV\n(.*?)\n?^TSV>>>\s*$", re.M | re.S)


def read_table(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {r["zh"]: r["es_mx"] for r in csv.DictReader(handle, delimiter="\t", quoting=csv.QUOTE_NONE)}


def write_table(path: Path, table: dict[str, str]) -> None:
    rows = ["zh\tes_mx"] + [f"{zh}\t{es}" for zh, es in sorted(table.items())]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def parse_result(result: str, requested: set[str]) -> dict[str, str]:
    """Las filas del TSV devuelto cuyo original es una cadena pedida."""
    match = TSV_BLOCK.search(result or "")
    rows = {}
    for line in (match.group(1).splitlines() if match else []):
        fields = line.split("\t")
        # Medido en la primera ejecución: un lote volvió con una columna de número
        # de línea delante. Se tolera esa sola desviación; el original sigue
        # teniendo que ser exactamente una cadena pedida.
        if len(fields) == 3 and fields[0].isdigit():
            fields = fields[1:]
        if len(fields) == 2 and fields[0] in requested and fields[1].strip():
            rows[fields[0]] = fields[1].strip()
    return rows


ENGLISH_WORD = re.compile(r"[A-Za-z]{3,}")


def introduced_english(table: dict[str, str]) -> list[tuple[str, str, list[str]]]:
    """Filas cuya traducción trae palabras inglesas que su original no trae.

    La herencia se mide fila por fila: `Agent` en «Agent 最小循环» es del
    original; `throughput` en la traducción de «吞吐量» no.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_prose_vocabulary as prose
    es_lex, en_lex = prose.load_lexicons()
    words = {w.lower() for es in table.values() for w in ENGLISH_WORD.findall(es)}
    dictionary = prose.SpanishDictionary(words)
    out = []
    for zh, es in sorted(table.items()):
        original = {w.lower() for w in ENGLISH_WORD.findall(zh)}
        new = [w for w in ENGLISH_WORD.findall(es)
               if w.lower() not in original and prose.singular(w.lower()) not in original
               and not dictionary.accepts(w.lower()) and prose.is_english(w.lower(), es_lex, en_lex)]
        if new:
            out.append((zh, es, new))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--missing", type=Path)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--bench", type=Path)
    parser.add_argument("--model", default="")
    parser.add_argument("--batch", type=int, default=80)
    parser.add_argument("--width", type=int, default=10)
    parser.add_argument("--memfree", default="3G")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--verify", action="store_true", help="solo revisa la tabla: inglés introducido por fila")
    args = parser.parse_args(argv)
    if args.verify:
        rows = introduced_english(read_table(args.table))
        for zh, es, new in rows:
            print(f"{zh}\t{es}\t{', '.join(new)}")
        print(f"translate_figure_text: {len(rows)} fila(s) con inglés que el original no trae", file=sys.stderr)
        return 1 if rows else 0
    if not FULL_MODEL_ID.match(args.model):
        print(f"translate_figure_text: `{args.model}` no es un identificador completo.", file=sys.stderr)
        return 2
    table = read_table(args.table)
    strings = [s for s in args.missing.read_text(encoding="utf-8").splitlines() if s.strip() and s not in table]
    if not strings:
        print("translate_figure_text: nada que traducir", file=sys.stderr)
        return 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    batches_dir = args.bench / "batches" / stamp
    batches_dir.mkdir(parents=True, exist_ok=True)
    batches = [strings[i:i + args.batch] for i in range(0, len(strings), args.batch)]
    items = []
    for k, batch in enumerate(batches):
        path = batches_dir / f"{k:03d}.txt"
        path.write_text("\n".join(batch) + "\n", encoding="utf-8")
        items.append(str(path.resolve()))
    out_dir = args.bench / "translate" / stamp
    runner = os.environ.get("TRANSLATION_RUNNER", str(REPO_ROOT / "tools" / "thyrox" / "run"))
    cmd = [runner, "headless-pool", "--prompt", str(PROMPT), "--out", str(out_dir), "--model", args.model,
           "--tools", "Read", "--width", str(args.width), "--memfree", args.memfree,
           "--timeout", str(args.timeout), "--max-turns", "4", "--cwd", str(REPO_ROOT)]
    print(f"translate_figure_text: {len(strings)} cadena(s) en {len(batches)} lote(s)", file=sys.stderr)
    subprocess.run(cmd, input="\n".join(items) + "\n", text=True)
    index = out_dir / "index.tsv"
    for line in (index.read_text(encoding="utf-8").splitlines() if index.is_file() else []):
        n, _sep, item = line.partition("\t")
        requested = set(Path(item).read_text(encoding="utf-8").splitlines())
        try:
            result = json.loads((out_dir / f"{n}.json").read_text(encoding="utf-8")).get("result", "")
        except (OSError, ValueError):
            result = ""
        table.update(parse_result(result, requested))
    write_table(args.table, table)
    left = [s for s in strings if s not in table]
    for s in left[:20]:
        print(f"translate_figure_text: sin traducción: {s}", file=sys.stderr)
    print(f"translate_figure_text: {len(strings) - len(left)} de {len(strings)} traducida(s)", file=sys.stderr)
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
