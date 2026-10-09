#!/usr/bin/env bash
# =============================================================================
# llama_direct_loop.sh: traduce el plan lote por lote contra el llama-server
# dedicado, sin coordinador y sin detenerse en un lote que pide juicio
# =============================================================================
#
# Cada lote pasa por `translate_wave.sh` con `TRANSLATION_RUNNER` apuntando a
# `llama_direct_runner.py`: traducir y retraducir lo corregido van al mismo
# servidor. Un lote que sale con 3 (pide juicio) no detiene el lazo: queda
# registrado en su ola y se sigue con el siguiente. Al terminar el plan se
# vuelve a empezar desde --from mientras algún lote haya traducido algo en la
# vuelta; una vuelta sin avance termina el lazo.
#
# Uso: llama_direct_loop.sh [--from N] [--to M] [--max-rounds R]
# Exit 0 plan recorrido sin avance pendiente · 4 el servidor no responde.
# =============================================================================
set -uo pipefail

from=26 to="" max_rounds=3
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) from="$2"; shift 2 ;;
        --to) to="$2"; shift 2 ;;
        --max-rounds) max_rounds="$2"; shift 2 ;;
        *) echo "llama_direct_loop: opción desconocida: $1" >&2; exit 2 ;;
    esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN=".claude/workbench/translation/plan.tsv"
[[ -n "$to" ]] || to=$(gawk -F'\t' 'NR > 1 {n = $1} END {print n}' "$PLAN")
export TRANSLATION_RUNNER="$HERE/llama_direct_runner.py"
URL="${LLAMA_DIRECT_URL:-http://127.0.0.1:11500}"
SETTLED="${LLAMA_DIRECT_SETTLED:-.claude/cache/ola/llama-direct.settled}"

# Fragmentos ya traducidos en todo el plan: la medida del avance de una vuelta.
translated_count() {
    find .claude/workbench/translation -path '*/chunks/*' -name '*.es.tex' 2>/dev/null | wc -l
}

for (( round = 1; round <= max_rounds; round++ )); do
    before=$(translated_count)
    for (( n = from; n <= to; n++ )); do
        if ! curl -sf --noproxy '*' "$URL/api/version" > /dev/null; then
            echo "llama_direct_loop: el servidor $URL no responde; se detiene en el lote $n" >&2
            exit 4
        fi
        echo "llama_direct_loop: vuelta $round, lote $n ($(date -u +%FT%TZ))" >&2
        # Lo que un reinicio dejó en disco sin recoger se escribe antes de pedir
        # nada al modelo (recover_pool_results.py).
        batch=$(gawk -F'\t' -v n="$n" '$1 == n {print $2}' "$PLAN")
        [[ -n "$batch" ]] && python3 "$HERE/recover_pool_results.py" "$batch"
        bash "$HERE/translate_wave.sh" --from "$n" --to "$n" --jobs 1 --compile
        echo "llama_direct_loop: lote $n salió $? ($(translated_count) fragmentos traducidos)" >&2
    done
    after=$(translated_count)
    echo "llama_direct_loop: vuelta $round: $before → $after fragmentos traducidos" >&2
    if (( after <= before )); then
        # Sin avance en una vuelta entera: lo que queda pide juicio, no otra
        # vuelta del modelo. La marca le dice a llama_direct_ensure.sh que no
        # relance el lazo sobre el mismo tramo cada cinco minutos.
        printf '%s\t%s\t%s\t%s\n' "$from" "$to" "$(date -u +%FT%TZ)" "$after" > "$SETTLED"
        echo "llama_direct_loop: lotes $from-$to sin avance; asentado en $SETTLED" >&2
        break
    fi
done
