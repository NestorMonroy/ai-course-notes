#!/usr/bin/env bash
# Fase 0 de la auditoría: estado real del entorno, sólo lectura. Cada bloque
# escribe un archivo en outputs/ con la orden que lo produjo en la cabecera.
set -uo pipefail
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../outputs" && pwd)"
CONSUMER=/home/user/ai-course-notes THYROX=/home/user/thyrox
section() { printf '# %s\n# medido: %s\n' "$1" "$(date -u +%FT%TZ)"; }

{ section "git de los dos repos"
  for r in "$CONSUMER" "$THYROX"; do
    echo "== $r"; git -C "$r" rev-parse --abbrev-ref HEAD; git -C "$r" rev-parse HEAD
    git -C "$r" status -sb | head -1; echo "sin commitear: $(git -C "$r" status --short | wc -l)"
  done; } > "$OUT/git.txt"

{ section "recursos del anfitrión (nproc, free -m, df -h)"
  nproc; free -m; df -h / /home 2>/dev/null; } > "$OUT/resources.txt"

{ section "procesos del carril y de thyrox vivos (ps)"
  ps -eo pid,etime,args | grep -E "[l]lama_direct|[t]ranslate_wave|[p]arallel|[t]ranslation_loop|[l]lama-server|[o]llama|[m]odel_coordinator|[h]eadless-pool" | cut -c1-220; } > "$OUT/processes.txt"

{ section "unidades de contenedor (podman-execution-execute observe containers)"
  (cd "$THYROX" && timeout 60 bash bin/podman-execution-execute observe containers) ; } > "$OUT/containers.json" 2>&1

{ section "servidores de inferencia: llama-server /props y Ollama /api/ps"
  curl -s --noproxy '*' --max-time 10 http://127.0.0.1:11600/props | python3 -c "
import json,sys; d=json.load(sys.stdin); g=d.get('default_generation_settings',{}); p=g.get('params',g)
print('llama-server 11600:', json.dumps({k:p.get(k) for k in ('temperature','top_p','top_k','min_p','presence_penalty','repeat_penalty','n_predict','reasoning_format')}), 'n_ctx', g.get('n_ctx'), 'alias', d.get('model_alias'))" 2>&1
  curl -s --noproxy '*' --max-time 10 http://127.0.0.1:11500/api/ps 2>&1 | head -c 600; echo; } > "$OUT/inference-servers.txt"

{ section "modelos locales: catálogo, cualificaciones del consumidor y artefactos"
  ls -la "$THYROX/.thyrox/models/artifacts/" 2>&1 | head -20
  python3 -c "import json; d=json.load(open('$CONSUMER/.thyrox/models/qualifications.json')); print(json.dumps(d, ensure_ascii=False)[:1500])" 2>&1; } > "$OUT/models.txt"

{ section "coordinador de modelos (bin/model_coordinator status)"
  (cd "$THYROX" && timeout 30 bash bin/model_coordinator status) 2>&1; } > "$OUT/coordinator.txt"

{ section "trabajos de thyrox-bg y del ledger (wait-jobs status)"
  (cd "$THYROX" && bash bin/wait-jobs status) 2>&1 | tail -40; } > "$OUT/jobs.txt"

{ section "plan y avance por lote (fragmentos .zh.tex / .es.tex)"
  printf 'orden\tlote\tzh\tes\n'
  awk -F'\t' 'NR>1 {print $1"\t"$2}' "$CONSUMER/.claude/workbench/translation/plan.tsv" | while IFS=$'\t' read -r n b; do
    d="$CONSUMER/.claude/workbench/translation/$b/chunks"
    printf '%s\t%s\t%s\t%s\n' "$n" "$b" "$(find "$d" -name '*.zh.tex' 2>/dev/null | wc -l)" "$(find "$d" -name '*.es.tex' 2>/dev/null | wc -l)"
  done; } > "$OUT/progress.tsv"
echo "fase 0: $(ls "$OUT" | wc -l) archivos en $OUT"
