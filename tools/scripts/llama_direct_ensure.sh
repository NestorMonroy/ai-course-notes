#!/usr/bin/env bash
# =============================================================================
# llama_direct_ensure.sh: deja en marcha el llama-server dedicado de es-MX y
# su lazo de traducción; idempotente
# =============================================================================
#
# Un reinicio del anfitrión mata el servidor y el lazo sin dejar marcador.
# Este guion mide antes de actuar y sólo levanta lo que falta:
#
#   servidor  `/api/version` en LLAMA_DIRECT_URL responde → no se toca;
#             si no, se lanza la unidad `llama-direct-es-mx` por thyrox-bg
#             (Ollama 0.35 con llama-server dentro, fuera del coordinador)
#   modelo    `/api/show` lo encuentra → no se toca; si no, `/api/create`
#             desde el blob montado (el GGUF de thyrox/.thyrox/models)
#   lazo      un `llama_direct_loop.sh` vivo → no se toca; si no, se lanza
#             desde --from con su log en .claude/cache/ola/
#
# Uso: llama_direct_ensure.sh [--from N]
# Exit 0 todo en marcha · 3 el servidor no respondió tras lanzarlo.
# =============================================================================
set -uo pipefail

from=26
[[ "${1:-}" == "--from" ]] && from="$2"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSUMER="$(cd "$HERE/../.." && pwd)"
THYROX="${THYROX_ROOT:-/home/user/thyrox}"
URL="${LLAMA_DIRECT_URL:-http://127.0.0.1:11500}"
MODEL="${LLAMA_DIRECT_MODEL:-qwen35-9b-es-mx}"
SHA=03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8
JOB=llama-direct-es-mx

alive() { curl -sf --noproxy '*' --max-time 5 "$URL/api/version" > /dev/null; }

if alive; then
    echo "llama_direct_ensure: servidor ya activo en $URL"
else
    # La memoria de la unidad deja margen al anfitrión (15 GiB): con 11 GiB el
    # typecheck de un commit en paralelo agotó la RAM y la VM se reinició.
    export OLLAMA_HOST="${URL#http://}" OLLAMA_MODELS=/root/.ollama/models OLLAMA_NOPRUNE=1 OLLAMA_NO_CLOUD=1 \
        OLLAMA_LOAD_TIMEOUT=30m OLLAMA_CONTEXT_LENGTH=32768 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_FLASH_ATTENTION=1 \
        OLLAMA_KEEP_ALIVE=-1 OLLAMA_NUM_PARALLEL=1 LLAMA_ARG_CACHE_RAM=0
    envs=()
    for name in OLLAMA_HOST OLLAMA_MODELS OLLAMA_NOPRUNE OLLAMA_NO_CLOUD OLLAMA_LOAD_TIMEOUT OLLAMA_CONTEXT_LENGTH \
                OLLAMA_KV_CACHE_TYPE OLLAMA_FLASH_ATTENTION OLLAMA_KEEP_ALIVE OLLAMA_NUM_PARALLEL LLAMA_ARG_CACHE_RAM; do
        envs+=(--env "$name")
    done
    (cd "$THYROX" && bash bin/thyrox-bg start "$JOB" --grace 10 --work ai-course-notes:es-mx/llama-direct \
        --kind workbench --image docker.io/ollama/ollama:0.35.0 --network host \
        --mount "$THYROX/.thyrox/models/artifacts/sha256-$SHA.gguf:/root/.ollama/models/blobs/sha256-$SHA:rw" \
        "${envs[@]}" --cpus 4 --memory-mib 9216 -- serve)
    for _ in $(seq 60); do alive && break; sleep 2; done
    alive || { echo "llama_direct_ensure: el servidor no respondió en $URL" >&2; exit 3; }
    echo "llama_direct_ensure: servidor lanzado en $URL"
fi

if curl -sf --noproxy '*' "$URL/api/show" -d "{\"model\":\"$MODEL\"}" > /dev/null; then
    echo "llama_direct_ensure: modelo $MODEL ya creado"
else
    curl -sf --noproxy '*' "$URL/api/create" \
        -d "{\"model\":\"$MODEL\",\"files\":{\"model.gguf\":\"sha256:$SHA\"},\"stream\":false}" > /dev/null \
        && echo "llama_direct_ensure: modelo $MODEL creado"
fi

if pgrep -f '[l]lama_direct_loop.sh' > /dev/null; then
    echo "llama_direct_ensure: lazo ya activo"
else
    log="$CONSUMER/.claude/cache/ola/llama-direct-$(date -u +%Y%m%dT%H%M%SZ).log"
    # setsid: el lazo no pertenece al grupo de procesos de quien llama, así que
    # sobrevive a que el cliente detenga ese comando.
    (cd "$CONSUMER" && setsid -f nohup uv run --locked bash "$HERE/llama_direct_loop.sh" --from "$from" \
        > "$log" 2>&1 < /dev/null &)
    echo "llama_direct_ensure: lazo lanzado desde el lote $from; log: $log"
fi
