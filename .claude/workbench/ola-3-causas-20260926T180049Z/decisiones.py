"""Aplica las decisiones de ruta 2 de la ola 3, una a la vez, y mide cada una.

Cada decisión agrega su fila de glosario o sus entradas de memoria mecánica,
barre fragmentos y notas, y se mide con `measure --decision` contra la
medición anterior (plan 2.1, sección 6).
"""
import json
import subprocess
import sys
from pathlib import Path

LOOP = ["python3", "tools/scripts/translation_loop.py"]
BENCH = Path(sys.argv[1])
GLOSSARY = Path("tools/lang/es-mx/glossary.tsv")
MEMORY = Path("tools/lang/es-mx/translation_memory.jsonl")


def mechanical(pattern, signal, search, replace):
    return {"patron": pattern, "senal_del_verificador": signal,
            "fix_generico": {"tipo": "mechanical", "buscar": search, "reemplazar": replace},
            "archivos_donde_ya_se_aplico": []}


DECISIONS = [
    ("glosario: commit y full-stack se conservan", [
        "commit\tkeep\tcommit\tregistro de cambios de git («mensaje de commit»)\tuso en el original zh",
        "full-stack\tkeep\tfull-stack\tque abarca frontend y backend\tuso en el original zh"], []),
    ("glosario: auditability → capacidad de auditoría", [
        "auditability\ttranslate\tcapacidad de auditoría\tque el comportamiento de un sistema pueda revisarse "
        "después\tdecisión editorial: ni auditable ni auditabilidad están en RLA-ES\tauditabilidad"], []),
    ("xeCJK con WenQuanYi Zen Hei de respaldo", [], [mechanical(
        "preámbulo es-MX sin fuente CJK de respaldo; FandolSong no tiene U+73FA", "compile:missing-glyph",
        "\\usepackage{xeCJK}\n\\setCJKmainfont{FandolSong-Regular.otf}\n",
        "% FandolSong no cubre algunos caracteres de nombres (U+73FA); WenQuanYi Zen Hei sí.\n"
        "\\usepackage[AutoFallBack=true]{xeCJK}\n\\setCJKmainfont{FandolSong-Regular.otf}\n"
        "\\setCJKfallbackfamilyfont{\\CJKrmdefault}{WenQuanYi Zen Hei}\n")]),
    ("U+FFFD: caracteres partidos por el modelo", [], [
        mechanical("carácter multibyte partido por el modelo", "compile:missing-glyph",
                   "est\ufffd\ufffd centrada", "está centrada"),
        mechanical("carácter multibyte partido por el modelo", "compile:missing-glyph",
                   "qu\ufffd\ufffd subagente", "qué subagente")]),
    ("nombre del programa: Ungrounded (不着边际)", [], [mechanical(
        "nombre chino del programa fuera de la forma «nombre (原文)»", "parity:residual-han",
        "Ungrounded 不着边际", "Ungrounded (不着边际)")]),
    ("forma prohibida «correr el», dos casos exactos", [], [
        mechanical("«correr» por ejecutar", "prose:forbidden:correr el",
                   "correr el modelo SFT", "ejecutar el modelo SFT"),
        mechanical("«correr» por ejecutar", "prose:forbidden:correr el",
                   "entre más pueda correr el Agent", "entre más tiempo pueda ejecutarse el Agent")]),
]


def run(args):
    result = subprocess.run(LOOP + args, capture_output=True, text=True)
    print(f"$ {' '.join(args[:3])} -> {result.returncode}\n{result.stderr[-1500:]}", flush=True)
    return result.returncode


# Reanudación: `sys.argv[2]` es la primera decisión por aplicar (base 1). Las ya
# medidas no se repiten, ni la medición inicial.
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
if START == 1:
    run(["measure", "--decision", "olas 2 y 3 (lo que cambiaron desde la medición anterior)"])
for number, (label, rows, entries) in enumerate(DECISIONS, 1):
    if number < START:
        continue
    if rows:
        with GLOSSARY.open("a", encoding="utf-8") as handle:
            handle.write("".join(r + "\n" for r in rows))
    if entries:
        with MEMORY.open("a", encoding="utf-8") as handle:
            handle.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
        run(["sweep", "--bench", str(BENCH), "--iteration", str(number)])
    code = run(["measure", "--decision", label])
    if code == 4:
        print(f"decisiones: «{label}» dio neto negativo; se detiene para revertirla", flush=True)
        sys.exit(4)
print("EXIT=0", flush=True)
