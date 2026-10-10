#!/usr/bin/env bash
# =============================================================================
# llama_direct_proof.sh: prueba LOCAL del carril llama-direct, fallando cerrado
# =============================================================================
#
# La misma cadena que `vm-utilization-audit-*/probes/local-proof.sh` de thyrox,
# para el carril que no pasa por el coordinador (llama_direct_ensure.sh):
#
#   modelo pedido (LLAMA_DIRECT_MODEL)
#   → artefacto del modelo: el blob GGUF montado tiene el SHA del catálogo
#   → runtime: el contenedor del servidor corre la imagen de Ollama POR DIGEST
#   → residencia: /api/ps tiene ese modelo cargado
#   → respuestas reales: el `model` de cada <n>.json del último translate/ del
#     lote es el pedido, con runtime llama-direct
#   → ningún resultado nombra un modelo remoto (claude, anthropic, gpt, gemini)
#
# Sólo con todos los eslabones sale `LOCAL_WORKER PROVEN`; si falta uno,
# `NOT_PROVEN <motivo>`. Sólo lee.
#
# Uso: llama_direct_proof.sh <lote>
#
# Ciega a: la calidad de la traducción (eso lo deciden los verificadores V0–V6
# del ciclo) y a qué petición atendió cada proceso: con un solo servidor por VM
# esa ceguera no cambia la conclusión.
# =============================================================================
set -uo pipefail

batch="${1:?lote del plan}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONSUMER="$(cd "$HERE/../.." && pwd)"
THYROX="${THYROX_ROOT:-/home/user/thyrox}"
URL="${LLAMA_DIRECT_URL:-http://127.0.0.1:11500}"
MODEL="${LLAMA_DIRECT_MODEL:-qwen35-9b-es-mx}"
SHA=03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8
IMAGE_DIGEST=sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01
emit() { printf '%s\t%s\n' "$1" "$2"; }
missing=()

emit NODE_ID "$(hostname)/$(cut -c1-8 /proc/sys/kernel/random/boot_id)"
emit BATCH "$batch"
emit REQUESTED_MODEL "$MODEL"

# Artefacto: el blob que el servidor monta es el GGUF del catálogo, medido por SHA.
gguf="$THYROX/.thyrox/models/artifacts/sha256-$SHA.gguf"
if [[ -f "$gguf" ]]; then
    got="$(sha256sum "$gguf" | awk '{print $1}')"
    emit MODEL_ARTIFACT_SHA256 "$got"
    [[ "$got" == "$SHA" ]] || missing+=("sha-artefacto")
else
    emit MODEL_ARTIFACT_SHA256 none; missing+=("sin-artefacto")
fi

# Runtime: el contenedor vivo del carril (dueño ai-course-notes.es-mx-llama-direct) con
# la imagen por digest. Un huérfano de un arranque anterior monta el mismo blob con la
# imagen por etiqueta (H-THYROX-642); elegir por montaje lo confundía con el servidor.
containers="$(cd "$THYROX" && timeout 30 bash bin/podman-execution-execute observe containers 2>/dev/null || echo '[]')"
unit="$(jq -c --arg d "@$IMAGE_DIGEST" '[.[] | select(.running and .labels["thyrox.owner-id"] == "ai-course-notes.es-mx-llama-direct" and (.image | endswith($d)))][0] // empty' <<<"$containers")"
[[ -n "$unit" ]] || unit="$(jq -c '[.[] | select(.running and .labels["thyrox.owner-id"] == "ai-course-notes.es-mx-llama-direct")][0] // empty' <<<"$containers")"
image="$(jq -r '.image // "none"' <<<"${unit:-{\}}")"
emit EXECUTION_UNIT "$(jq -r '.name // "none"' <<<"${unit:-{\}}")"
emit RUNTIME_IDENTITY "$image"
[[ "$image" == *"@$IMAGE_DIGEST" ]] || missing+=("imagen-no-por-digest")

# Residencia: el servidor tiene el modelo pedido cargado.
loaded="$(curl -sf --noproxy '*' --max-time 10 "$URL/api/ps" | jq -r '.models[].name' 2>/dev/null | paste -sd, -)"
emit RESIDENT_MODELS "${loaded:-none}"
grep -q "^$MODEL\(:latest\)\?$" <<<"$(tr ',' '\n' <<<"$loaded")" || missing+=("modelo-no-residente")

# Respuestas reales del último translate/ del lote que escribió el runner llama-direct.
bench="$CONSUMER/.claude/workbench/translation/$batch/translate"
run=""
for d in $(ls -td "$bench"/*/ 2>/dev/null); do
    if jq -e 'select(.runtime == "llama-direct" and .subtype == null)' "$d"*.json >/dev/null 2>&1; then run="$d"; break; fi
done
served="" responses=0 errors=0 remote=no
if [[ -n "$run" ]]; then
    # Sólo cuenta una traducción real: sin `subtype` de error y con el fragmento entre
    # marcadores. Un error de conexión también lleva runtime llama-direct; contarlo
    # dio un PROVEN falso cuando el servidor murió a mitad del lote (H-THYROX-642).
    # «Real» es lo que el ciclo aceptaría: el mismo `extract_translation` y
    # `structure_problem` del lazo. Mirar sólo `<<<ES` contó 6 respuestas que el
    # lazo rechazaba por cerrar con la cerca en vez de `ES>>>`.
    accepted="$(python3 - "$run" "$HERE" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
import llama_direct_runner as runner, translation_loop as loop
run = Path(sys.argv[1])
for line in (run / "index.tsv").read_text(encoding="utf-8").splitlines():
    n, _, zh = line.partition("\t")
    try:
        record = json.loads((run / f"{n}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    if record.get("runtime") != "llama-direct" or record.get("subtype"):
        continue
    text = loop.extract_translation(runner.close_markers(record.get("result", "") or ""))
    if text is not None and not loop.structure_problem(Path(zh).read_text(encoding="utf-8"), text):
        print(record.get("model", ""))
PY
)"
    served="$(sed '/^$/d' <<<"$accepted" | sort | uniq -c | awk '{print $2"×"$1}' | paste -sd, -)"
    responses="$(sed '/^$/d' <<<"$accepted" | wc -l)"
    errors="$(jq -r 'select(.runtime == "llama-direct" and .subtype != null) | .subtype' "$run"*.json 2>/dev/null | wc -l)"
    jq -r '.model // empty' "$run"*.json 2>/dev/null | grep -qiE 'claude|anthropic|gpt|gemini' && remote=yes
fi
emit RUN_DIR "${run:-none}"
emit ACTUAL_SERVED_MODEL "${served:-none} (responses=$responses, errors=${errors:-0})"
emit REMOTE_MODEL_IN_RESULTS "$remote"
(( responses > 0 )) || missing+=("sin-respuestas")
[[ "$remote" == no ]] || missing+=("modelo-remoto")
[[ -z "$served" || "$served" == "$MODEL×"* && "$served" != *,* ]] || missing+=("modelo-servido-distinto")

if (( ${#missing[@]} == 0 )); then
    emit LOCAL_WORKER PROVEN
else
    emit LOCAL_WORKER "NOT_PROVEN ($(IFS=,; echo "${missing[*]}"))"
fi
