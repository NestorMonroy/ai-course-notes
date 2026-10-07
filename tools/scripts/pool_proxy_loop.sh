#!/usr/bin/env bash
# =============================================================================
# pool_proxy_loop.sh: traduce el plan lote por lote con el modelo del
# proveedor por el pool, del último lote hacia atrás
# =============================================================================
#
# Corre junto a llama_direct_loop.sh, que avanza desde el lote 26 hacia
# adelante: recorrer en sentido contrario evita que los dos traduzcan el mismo
# lote a la vez. Un fragmento que ya tiene `.es.tex` no vuelve a traducirse,
# así que cuando se cruzan cada uno sólo toma lo pendiente.
#
# Uso: pool_proxy_loop.sh [--from N] [--to M]   (desciende de --from a --to)
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN=".claude/workbench/translation/plan.tsv"
from="" to=27
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) from="$2"; shift 2 ;;
        --to) to="$2"; shift 2 ;;
        *) echo "pool_proxy_loop: opción desconocida: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$from" ]] || from=$(gawk -F'\t' 'NR > 1 {n = $1} END {print n}' "$PLAN")
export TRANSLATION_RUNNER="$HERE/pool_proxy_runner.sh"

for (( n = from; n >= to; n-- )); do
    echo "pool_proxy_loop: lote $n ($(date -u +%FT%TZ))" >&2
    # Sin --compile: el sparse-checkout trae sólo los .tex y .srt de estos lotes;
    # compilar exige sus figuras y se hace después, con ellas en disco.
    # Lo que un reinicio dejó en disco sin recoger se escribe antes de pedir
    # nada al modelo (recover_pool_results.py).
    batch=$(gawk -F'\t' -v n="$n" '$1 == n {print $2}' "$PLAN")
    [[ -n "$batch" ]] && python3 "$HERE/recover_pool_results.py" "$batch"
    bash "$HERE/translate_wave.sh" --from "$n" --to "$n" --jobs 1
    echo "pool_proxy_loop: lote $n salió $?" >&2
done
