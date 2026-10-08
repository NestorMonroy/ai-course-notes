#!/usr/bin/env bash
# =============================================================================
# pool_proxy_runner.sh: TRANSLATION_RUNNER que traduce con un modelo del
# proveedor (claude-cli por el proxy local) a través de headless-pool
# =============================================================================
#
# translation_loop.py invoca al runner con la línea de la ruta local
# (`--execution unit --work-reference … --reasoning-effort low`). Aquí se
# reescribe hacia la ruta del proxy, la misma que usan los arreglos de código:
#
#   --execution host     el ítem corre en el anfitrión, no en una unidad
#   sin --work-reference sólo aplica con --execution unit
#   --reasoning-effort   POOL_PROXY_EFFORT (high → claude-opus-5-5)
#   --model-policy       model-policy-proxy.json: respaldo en claude-cli
#   --width              POOL_PROXY_WIDTH (4)
#
# El modelo lo deriva el selector y headless-pool lo anuncia; cada `<n>.json`
# lo registra, así el par del dataset declara su traductor.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSUMER="$(cd "$HERE/../.." && pwd)"
POLICY="${POOL_PROXY_POLICY:-$CONSUMER/tools/lang/es-mx/model-policy-proxy.json}"
EFFORT="${POOL_PROXY_EFFORT:-high}"
WIDTH="${POOL_PROXY_WIDTH:-4}"

[[ "${1:-}" == "headless-pool" ]] && shift
args=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --execution|--work-reference|--reasoning-effort|--task-class|--model-policy|--width) shift 2 ;;
        *) args+=("$1"); shift ;;
    esac
done
exec "$CONSUMER/tools/thyrox/run" headless-pool "${args[@]}" \
    --execution host --reasoning-effort "$EFFORT" --model-policy "$POLICY" --width "$WIDTH"
