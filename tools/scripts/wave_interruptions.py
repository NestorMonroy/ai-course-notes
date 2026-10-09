#!/usr/bin/env python3
"""Registra las olas que murieron antes de que Parallel escribiera sus filas.

GNU Parallel escribe la fila de un trabajo en ``joblog.tsv`` sólo cuando el
trabajo termina. Si el anfitrión se reinicia a mitad de una ola, ``joblog.tsv``
queda con la cabecera sola y ``translate_wave.sh``, que decide qué falló por la
columna 7, no ve ninguna falla: la ola parece vacía, no interrumpida.

Al arrancar una ola, ``translate_wave.sh`` llama a este módulo. Cada ola
anterior que no está viva y tiene lotes de ``batches.txt`` sin fila en su
``joblog.tsv`` recibe ``interrupted.tsv``, con una fila por lote. El
``joblog.tsv`` no se toca: es la salida de Parallel y una fila inventada se
leería como suya.

Una ola está viva si algún proceso nombra su directorio (por ruta, no por nombre)
en la línea de comando:
Parallel lleva ``--joblog <ola>/joblog.tsv`` mientras corre algún lote. La
comprobación importa porque dos lazos (llama-direct y el pool) lanzan olas sobre
el mismo árbol.

Ciega a: la causa de la muerte (reinicio, falta de memoria, un `kill`), que no
deja rastro en la ola; y a la hora real de una ola clonada: ``last_output_utc``
es el `mtime` de ``salida/``, que en un clon es la hora del checkout.

Uso: wave_interruptions.py <dir de olas> <ola actual>
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Callable

COLUMNS = ("batch", "detected_at", "detected_by", "last_output_utc", "reason")
REASON = "sin fila en joblog.tsv y sin proceso vivo: la ola murió antes de que el lote terminara"


def process_alive(wave: Path) -> bool:
    """¿Algún proceso, distinto de éste, nombra la ola en su línea de comando?

    Se compara la ruta, no el nombre: dos árboles pueden tener una ola con el
    mismo sello de tiempo. Un argumento relativo se resuelve contra el ``cwd``
    del proceso, porque Parallel recibe ``--joblog`` relativo a la raíz.
    """
    target = wave.resolve()
    own = os.getpid()
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == own:
            continue
        try:
            args = (proc / "cmdline").read_bytes().split(b"\0")
            candidates = [a.decode(errors="replace") for a in args if wave.name.encode() in a]
            if not candidates:
                continue
            cwd = Path(os.readlink(proc / "cwd"))
        except OSError:
            continue
        for arg in candidates:
            path = (cwd / arg).resolve()
            if path == target or target in path.parents:
                return True
    return False


def finished_batches(joblog: Path) -> set[str]:
    """Lotes con fila en el joblog: la última palabra de la columna Command."""
    if not joblog.is_file():
        return set()
    rows = joblog.read_text(encoding="utf-8").splitlines()[1:]
    return {row.split("\t")[-1].split()[-1] for row in rows if row.strip()}


def last_output(wave: Path, batch: str) -> str:
    """La última escritura del lote en ``salida/``, en UTC; ``-`` si no hay."""
    times = [p.stat().st_mtime for p in (wave / "salida").glob(f"*/{batch}/*") if p.is_file()]
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(max(times))) if times else "-"


def record(waves: Path, current: Path, alive: Callable[[Path], bool] = process_alive) -> list[tuple[str, str]]:
    """Escribe ``interrupted.tsv`` en cada ola interrumpida; devuelve (ola, lote)."""
    recorded = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for wave in sorted(p for p in waves.iterdir() if p.is_dir()):
        batches_file = wave / "batches.txt"
        if wave.resolve() == current.resolve() or (wave / "interrupted.tsv").exists() or not batches_file.is_file():
            continue
        batches = [b for b in batches_file.read_text(encoding="utf-8").split() if b]
        missing = [b for b in batches if b not in finished_batches(wave / "joblog.tsv")]
        if not missing or alive(wave):
            continue
        lines = ["\t".join(COLUMNS)]
        lines += ["\t".join((b, now, current.name, last_output(wave, b), REASON)) for b in missing]
        (wave / "interrupted.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        recorded += [(wave.name, b) for b in missing]
    return recorded


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    for wave, batch in record(Path(argv[0]), Path(argv[1])):
        print(f"translate_wave: la ola {wave} se interrumpió con el lote {batch} sin terminar; "
              f"queda en {wave}/interrupted.tsv", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
