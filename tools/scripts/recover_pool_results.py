#!/usr/bin/env python3
"""Recupera las traducciones que un runner dejó en disco sin que el ciclo las recogiera.

``translation_loop.py`` escribe los ``.es.tex`` sólo cuando el runner termina
el lote entero. Un reinicio del anfitrión a mitad deja las respuestas en los
``<n>.json`` de ``translate/<stamp>/`` y ningún fragmento escrito. En el caso
de headless-pool es peor: el ``index.tsv`` que asocia ``<n>`` con su fragmento
vive en el runtime del pool (``<thyrox>/.thyrox/runtime/pool/<clave>-*``) y
sólo llega a la salida al cerrar la ejecución.

Por cada ``translate/<stamp>/`` del lote, este guion toma su ``index.tsv`` (o,
si falta, el del runtime cuya clave es el sha1 de la ruta de salida, la misma
derivación que ``pool_lifecycle.out_key``) y escribe el ``.es.tex`` de cada
respuesta válida con las mismas verificaciones que ``collect_results``. No
toca un fragmento que ya tiene ``.es.tex`` ni uno con corrección más nueva que
la respuesta: esos los decide el ciclo.

Uso: recover_pool_results.py <lote>...
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llama_direct_runner  # noqa: E402
import translation_loop as loop  # noqa: E402

THYROX_ROOT = Path(os.environ.get("THYROX_ROOT", "/home/user/thyrox"))


def runtime_index(out_dir: Path) -> Path | None:
    """El índice vivo del pool que escribió en ``out_dir``, el más reciente."""
    key = hashlib.sha1(str(out_dir.resolve()).encode()).hexdigest()[:12]
    runs = sorted((THYROX_ROOT / ".thyrox" / "runtime" / "pool").glob(f"{key}-*"), reverse=True)
    for run in runs:
        if (run / "index.tsv").is_file():
            return run / "index.tsv"
    return None


def recover(batch: str) -> tuple[int, int]:
    bench = loop.batch_bench(batch)
    # Un lote que el ciclo aún no preparó no tiene nada que recuperar.
    if not (bench / "units.tsv").is_file():
        return 0, 0
    targets = {row[3]: row[4] for row in
               (l.split("\t") for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines() if l.strip())}
    written = rejected = 0
    for out_dir in sorted((bench / "translate").glob("*/")):
        index = out_dir / "index.tsv"
        if not index.is_file():
            index = runtime_index(out_dir)
        if index is None:
            continue
        for line in index.read_text(encoding="utf-8").splitlines():
            key, _, zh = line.partition("\t")
            target = targets.get(zh)
            result_file = out_dir / f"{key}.json"
            if not target or Path(target).exists() or not result_file.is_file():
                continue
            correction = Path(zh.replace(".zh.tex", ".correccion.md"))
            if correction.is_file() and correction.stat().st_mtime > result_file.stat().st_mtime:
                continue
            try:
                record = json.loads(result_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            result = record.get("result", "") or ""
            # El carril llama-direct cierra con la cerca en vez de `ES>>>` en las
            # respuestas anteriores a `close_markers`; el runner las cierra igual.
            if record.get("runtime") == "llama-direct":
                result = llama_direct_runner.close_markers(result)
            text = loop.extract_translation(result)
            if text is None or loop.structure_problem(Path(zh).read_text(encoding="utf-8"), text):
                rejected += 1
                continue
            Path(target).write_text(text, encoding="utf-8")
            written += 1
    return written, rejected


def main(argv: list[str]) -> int:
    for batch in argv:
        written, rejected = recover(batch)
        print(f"recover_pool_results: {batch}: {written} fragmento(s) escritos, {rejected} rechazado(s)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
