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
#   lazo      un `llama_direct_loop.sh` vivo → no se toca; un tramo asentado
#             (`llama-direct.settled` con el mismo --from/--to: una vuelta
#             sin avance, lo que queda pide juicio) → no se relanza; si no,
#             se lanza desde --from con su log en .claude/cache/ola/
#
# Uso: llama_direct_ensure.sh [--from N]
# Exit 0 todo en marcha · 3 el servidor no respondió tras lanzarlo.
# =============================================================================
set -uo pipefail

# El carril de esta VM (ES-A): el lote 26 quedó asentado el 2026-10-09 y ES-B
# y ES-C entregaron los lotes 27–33 sin modelo (es-mx-n-vm-analysis-20261008T015000,
# «Auditoría y consolidación»), así que el 9B local los toma.
from=27 to=33
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from) from="$2"; shift 2 ;;
        --to) to="$2"; shift 2 ;;
        *) echo "llama_direct_ensure: opción desconocida: $1" >&2; exit 2 ;;
    esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSUMER="$(cd "$HERE/../.." && pwd)"
THYROX="${THYROX_ROOT:-/home/user/thyrox}"
# El runtime del carril: llama-server (llama.cpp b11277) por defecto; Ollama 0.35
# queda declarado como alternativa (LLAMA_DIRECT_RUNTIME=ollama).
RUNTIME="${LLAMA_DIRECT_RUNTIME:-llama-server}"
MODEL="${LLAMA_DIRECT_MODEL:-qwen35-9b-es-mx}"
SHA=03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8
GGUF="$THYROX/.thyrox/models/artifacts/sha256-$SHA.gguf"
if [[ "$RUNTIME" == llama-server ]]; then
    URL="${LLAMA_DIRECT_URL:-http://127.0.0.1:11600}"
    API=openai
    JOB=llama-server-es-mx
    # Espejo de Docker Hub de runtime-images.json («llama-server» b11277), por digest:
    # HEAD anónimo 200 con el mismo digest, verificado el 2026-10-10.
    IMAGE="${LLAMA_DIRECT_IMAGE:-docker.io/th3rox/cache-ggml-org--llama.cpp@sha256:6d607629e3dd5e85f45c43d1494648126cb3f93f2122c9cd53f43242c94cde14}"
    alive() { curl -sf --noproxy '*' --max-time 5 "$URL/health" > /dev/null; }
else
    URL="${LLAMA_DIRECT_URL:-http://127.0.0.1:11500}"
    API=ollama
    JOB=llama-direct-es-mx
    # Por digest, nunca por etiqueta: el espejo th3rox/cache-ollama--ollama conserva este
    # mismo digest (runtime-images.json), verificado en Docker Hub el 2026-10-08.
    IMAGE="${LLAMA_DIRECT_IMAGE:-docker.io/ollama/ollama@sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01}"
    alive() { curl -sf --noproxy '*' --max-time 5 "$URL/api/version" > /dev/null; }
fi

if alive; then
    echo "llama_direct_ensure: servidor ($RUNTIME) ya activo en $URL"
elif [[ "$RUNTIME" == llama-server ]]; then
    # Perfil de la ficha Qwen3.5-9B «Instruct (non-thinking) for general tasks» fijado
    # en el servidor (propuesta de VM W, qwen35-card-vm-w.md §5): el cliente no lo
    # reenvía. LD_LIBRARY_PATH=/app porque sin él el binario sale 127 (H-THYROX-639);
    # LLAMA_ARG_THINK y no REASONING_FORMAT, que b11277 ignora (H-THYROX-638).
    export LD_LIBRARY_PATH=/app
    port="${URL##*:}"
    (cd "$THYROX" && bash bin/thyrox-bg start "$JOB" --grace 10 --work ai-course-notes:es-mx/llama-server \
        --kind workbench --image "$IMAGE" --network host \
        --mount "$GGUF:/model.gguf:ro" --env LD_LIBRARY_PATH --cpus 4 --memory-mib 9216 -- \
        -m /model.gguf --alias "$MODEL" --host 127.0.0.1 --port "$port" \
        -c 32768 -np 1 -n 12288 --cache-type-k q8_0 --cache-type-v q8_0 -fa on \
        --jinja --chat-template-kwargs '{"enable_thinking":false}' \
        --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0)
    # La primera carga lee 5.6 GB del disco: con la caché fría tarda minutos.
    for _ in $(seq 300); do alive && break; sleep 2; done
    alive || { echo "llama_direct_ensure: el servidor no respondió en $URL" >&2; exit 3; }
    echo "llama_direct_ensure: servidor llama-server lanzado en $URL"
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
        --kind workbench --image "$IMAGE" --network host \
        --mount "$GGUF:/root/.ollama/models/blobs/sha256-$SHA:rw" \
        "${envs[@]}" --cpus 4 --memory-mib 9216 -- serve)
    for _ in $(seq 60); do alive && break; sleep 2; done
    alive || { echo "llama_direct_ensure: el servidor no respondió en $URL" >&2; exit 3; }
    echo "llama_direct_ensure: servidor ollama lanzado en $URL"
fi

if [[ "$RUNTIME" == llama-server ]]; then
    :  # llama-server carga el GGUF al arrancar con --alias; no hay modelo que crear
elif curl -sf --noproxy '*' "$URL/api/show" -d "{\"model\":\"$MODEL\"}" > /dev/null; then
    echo "llama_direct_ensure: modelo $MODEL ya creado"
else
    curl -sf --noproxy '*' "$URL/api/create" \
        -d "{\"model\":\"$MODEL\",\"files\":{\"model.gguf\":\"sha256:$SHA\"},\"stream\":false}" > /dev/null \
        && echo "llama_direct_ensure: modelo $MODEL creado"
fi

# Un tramo que el lazo ya asentó (una vuelta sin avance) no se relanza: lo que
# queda en él pide juicio. Otro --from/--to, o retirar la marca, lo reabre.
SETTLED="$CONSUMER/.claude/cache/ola/llama-direct.settled"
if pgrep -f '[l]lama_direct_loop.sh' > /dev/null; then
    echo "llama_direct_ensure: lazo ya activo"
elif [[ -f "$SETTLED" ]] && gawk -F'\t' -v a="$from" -v b="$to" '$1 == a && $2 == b {ok = 1} END {exit !ok}' "$SETTLED"; then
    echo "llama_direct_ensure: lazo ya asentado en los lotes $from-$to ($(cut -f3 "$SETTLED")); no se relanza"
else
    log="$CONSUMER/.claude/cache/ola/llama-direct-$(date -u +%Y%m%dT%H%M%SZ).log"
    # setsid: el lazo no pertenece al grupo de procesos de quien llama, así que
    # sobrevive a que el cliente detenga ese comando.
    export LLAMA_DIRECT_URL="$URL" LLAMA_DIRECT_API="$API" LLAMA_DIRECT_MODEL="$MODEL"
    (cd "$CONSUMER" && setsid -f nohup uv run --locked bash "$HERE/llama_direct_loop.sh" --from "$from" --to "$to" \
        > "$log" 2>&1 < /dev/null &)
    echo "llama_direct_ensure: lazo lanzado desde el lote $from; log: $log"
fi
