#!/usr/bin/env bash
# =============================================================================
# translate_wave.sh: una ola de lotes del plan, en paralelo con GNU Parallel
# =============================================================================
#
#   uv run --locked bash tools/scripts/translate_wave.sh --from N --to M [--jobs J] --model <id> [--compile]
#
# Con `uv run`: el `python3` de la ola tiene que ser el del proyecto, porque el
# verificador usa los léxicos de spaCy.
#
# Toma los lotes N..M de `.claude/workbench/translation/plan.tsv` y lanza un
# `translation_loop.py advance --no-sweep` por lote con GNU Parallel (`-j J`).
# La anchura contra la API se reparte entre los J trabajos (10 // J cada uno),
# porque el techo de concurrencia es uno solo. El registro de la ola (joblog de
# Parallel, barrido y triage) queda en `translation/waves/<fecha>/`.
#
# El barrido (ruta 1) y el triage (ruta 2) corren una sola vez al final: el
# barrido reescribe la memoria y es para todo el corpus, así que no puede correr
# por lote en paralelo. Un lote que sale con 3 pide juicio y es lo esperado; la
# ola falla solo si un lote sale con otro código (verificación incompleta o error).
# =============================================================================
set -uo pipefail

from="" to="" jobs=3 model="" compile=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) from="$2"; shift 2 ;;
        --to) to="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --model) model="$2"; shift 2 ;;
        --compile) compile="--compile"; shift ;;
        *) echo "translate_wave: opción desconocida: $1" >&2; exit 2 ;;
    esac
done
if [[ -z "$from" || -z "$to" || -z "$model" ]]; then
    echo "uso: $0 --from N --to M [--jobs J] --model <id> [--compile]" >&2
    exit 2
fi

LOOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/translation_loop.py"
PLAN=".claude/workbench/translation/plan.tsv"
WAVE=".claude/workbench/translation/waves/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$WAVE"
width=$(( 10 / jobs )); (( width < 1 )) && width=1

# Los lotes de la ola, uno por línea: el nombre es la segunda columna del plan.
awk -F'\t' -v a="$from" -v b="$to" 'NR > 1 && $1 >= a && $1 <= b {print $2}' "$PLAN" > "$WAVE/batches.txt"
if [[ ! -s "$WAVE/batches.txt" ]]; then
    echo "translate_wave: el plan no tiene lotes entre $from y $to" >&2
    exit 2
fi

parallel --will-cite -j "$jobs" --joblog "$WAVE/joblog.tsv" --results "$WAVE/salida" \
    python3 "$LOOP" advance --batch {} --model "$model" --width "$width" --no-sweep $compile \
    :::: "$WAVE/batches.txt"

python3 "$LOOP" sweep --bench "$WAVE" --iteration 1 > "$WAVE/sweep.log" 2>&1
python3 "$LOOP" triage > "$WAVE/triage.log" 2>&1
cp .claude/workbench/translation/triage.tsv "$WAVE/triage.tsv"

# Exitval es la columna 7 del joblog: 0 limpio, 3 pide juicio; otra cosa es falla.
failed=$(awk -F'\t' 'NR > 1 && $7 != 0 && $7 != 3 {print $NF}' "$WAVE/joblog.tsv")
awk -F'\t' 'NR > 1 {n[$7]++} END {for (c in n) printf "translate_wave: exit %s en %d lote(s)\n", c, n[c]}' \
    "$WAVE/joblog.tsv" >&2
if [[ -n "$failed" ]]; then
    echo "translate_wave: lotes con falla: $failed" >&2
    exit 1
fi
exit 0
