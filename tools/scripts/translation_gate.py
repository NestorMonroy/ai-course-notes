#!/usr/bin/env python3
"""Los gates del ciclo de traduccion es-MX (`docs/ES_MX_TRANSLATION_PLAN.md`).

    translation_gate.py memory --signals S.jsonl [--memory M.jsonl]
    translation_gate.py sweep  --iteration N --sweep-log W.jsonl [--memory M.jsonl]
    translation_gate.py batch  --signals S.jsonl --review-log R.jsonl
    translation_gate.py report --iteration-log I.jsonl

Un paso que se puede saltar, eventualmente se salta. Por eso escribir la
memoria (GATE A), barrer el corpus con ella (GATE B) y cerrar un lote limpio y
revisado (GATE C) no son pasos de una secuencia: salen 2 y detienen el ciclo.
`report` publica iteraciones contra notas con senal y marca el modo reactivo.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY = REPO_ROOT / "tools" / "lang" / "es-mx" / "translation_memory.jsonl"
REQUIRED = ("patron", "senal_del_verificador", "fix_generico", "archivos_donde_ya_se_aplico")
FIX_TYPES = {"glossary", "prohibited", "prompt", "mechanical", "manual"}
# El ciclo es reactivo si da casi una iteracion por nota con senal.
REACTIVE_RATIO = 0.75


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stop(gate: str, lines: list[str]) -> int:
    print(f"{gate} BLOQUEADO — el ciclo no continua:", file=sys.stderr)
    for line in lines:
        print(f"  {line}", file=sys.stderr)
    return 2


def entry_problems(entry: dict, number: int) -> list[str]:
    problems = [f"entrada {number}: falta o esta vacio `{k}`" for k in REQUIRED if not entry.get(k)]
    fix = entry.get("fix_generico")
    if isinstance(fix, dict) and fix.get("tipo") not in FIX_TYPES:
        problems.append(f"entrada {number}: fix_generico.tipo `{fix.get('tipo')}` no es uno de {sorted(FIX_TYPES)}")
    elif fix is not None and not isinstance(fix, dict):
        problems.append(f"entrada {number}: fix_generico tiene que ser un objeto con `tipo`")
    if entry.get("archivos_donde_ya_se_aplico") is not None and not isinstance(entry.get("archivos_donde_ya_se_aplico"), list):
        problems.append(f"entrada {number}: archivos_donde_ya_se_aplico tiene que ser una lista")
    return problems


def covered(signal: str, memory: list[dict]) -> bool:
    return any(fnmatch.fnmatchcase(signal, e.get("senal_del_verificador", "")) for e in memory)


def cmd_memory(args) -> int:
    memory = read_jsonl(args.memory)
    problems = [p for n, e in enumerate(memory, 1) for p in entry_problems(e, n)]
    if problems:
        return stop("GATE A", problems)
    new = sorted({s["signal"] for s in read_jsonl(args.signals) if not covered(s["signal"], memory)})
    if new:
        return stop("GATE A", [f"senal sin patron en la memoria: {s}" for s in new]
                    + ["corrige la causa raiz y escribe su entrada con los 4 campos antes del paso 4"])
    print(f"GATE A: {len(memory)} entrada(s) valida(s); toda senal tiene patron.")
    return 0


def cmd_sweep(args) -> int:
    memory = read_jsonl(args.memory)
    swept = {r.get("senal_del_verificador") for r in read_jsonl(args.sweep_log) if r.get("iteration") == args.iteration}
    missing = [e["senal_del_verificador"] for e in memory if e.get("senal_del_verificador") not in swept]
    if missing:
        return stop("GATE B", [f"iteracion {args.iteration}: patron sin barrido: {m}" for m in missing]
                    + ["barre TODAS las notas es-MX con cada patron antes de volver al paso 2"])
    print(f"GATE B: iteracion {args.iteration}, {len(memory)} patron(es) barrido(s).")
    return 0


def cmd_batch(args) -> int:
    open_signals = read_jsonl(args.signals)
    review = read_jsonl(args.review_log)
    lines = []
    if open_signals:
        lines.append(f"{len(open_signals)} senal(es) abierta(s); primera: {open_signals[0]['signal']} en {open_signals[0]['note']}")
    if not review:
        lines.append("sin revision visual registrada del lote (V7 por muestreo)")
    if lines:
        return stop("GATE C", lines)
    print(f"GATE C: lote limpio; {len(review)} nota(s) con revision visual.")
    return 0


def cmd_report(args) -> int:
    log = read_jsonl(args.iteration_log)
    iterations = len(log)
    touched = sum(r.get("notes_with_signals", 0) for r in log)
    written = sum(r.get("memory_entries_written", 0) for r in log)
    ratio = iterations / touched if touched else 0.0
    reactive = iterations > 2 and ratio >= REACTIVE_RATIO
    print(f"iteraciones={iterations} notas_con_senal={touched} entradas_de_memoria={written} "
          f"razon={ratio:.2f}{'  REACTIVO: casi una iteracion por nota; el barrido no hizo su trabajo' if reactive else ''}")
    return 1 if reactive else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("memory"); p.add_argument("--signals", type=Path, required=True)
    p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY); p.set_defaults(func=cmd_memory)
    p = sub.add_parser("sweep"); p.add_argument("--iteration", type=int, required=True)
    p.add_argument("--sweep-log", type=Path, required=True)
    p.add_argument("--memory", type=Path, default=DEFAULT_MEMORY); p.set_defaults(func=cmd_sweep)
    p = sub.add_parser("batch"); p.add_argument("--signals", type=Path, required=True)
    p.add_argument("--review-log", type=Path, required=True); p.set_defaults(func=cmd_batch)
    p = sub.add_parser("report"); p.add_argument("--iteration-log", type=Path, required=True)
    p.set_defaults(func=cmd_report)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
