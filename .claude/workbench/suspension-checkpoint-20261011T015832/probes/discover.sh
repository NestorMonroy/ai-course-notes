#!/usr/bin/env bash
# Descubrimiento de solo lectura para la suspensión controlada.
# Escribe un inventario por clase en outputs/; repetible: cada ejecución
# reescribe los inventarios con el estado de ese momento y deja la hora en
# outputs/discovered-at.txt. No detiene, no limpia, no reconcilia nada.
set -uo pipefail
BANK="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$BANK/outputs"
THYROX="${THYROX:-/home/user/thyrox}"
CONSUMER="${CONSUMER:-/home/user/ai-course-notes}"
mkdir -p "$OUT"
date -u +%FT%TZ > "$OUT/discovered-at.txt"
{ echo "uptime_since	$(uptime -s)"; echo "boot_id	$(cat /proc/sys/kernel/random/boot_id)"; } >> "$OUT/discovered-at.txt"

# 1. Repositorios: rama, HEAD, remoto, divergencia, cambios y operaciones a medias.
{
  printf 'repo\tbranch\thead\tremote_head\tahead\tbehind\tstaged\tunstaged\tuntracked\tin_progress_op\n'
  for repo in "$THYROX" "$CONSUMER"; do
    cd "$repo" || continue
    b=$(git branch --show-current)
    h=$(git rev-parse HEAD)
    r=$(git rev-parse "origin/$b" 2>/dev/null || echo none)
    ab=$(git rev-list --left-right --count "HEAD...origin/$b" 2>/dev/null || echo "? ?")
    st=$(git diff --cached --name-only | wc -l)
    un=$(git diff --name-only | wc -l)
    ut=$(git ls-files --others --exclude-standard | wc -l)
    op=none
    for f in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
      [[ -e "$(git rev-parse --git-dir)/$f" ]] && op=$f
    done
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$(git remote get-url origin)" "$b" "$h" "$r" "${ab% *}" "${ab#* }" "$st" "$un" "$ut" "$op"
  done
} > "$OUT/repositories.tsv"

# 2. Worktrees y ramas remotas con su último commit.
{ for repo in "$THYROX" "$CONSUMER"; do (cd "$repo" && echo "## $repo" && git worktree list --porcelain); done; } > "$OUT/worktrees.txt"
{
  printf 'repo\tbranch\thead\tcommitted_at\tsubject\n'
  for repo in "$THYROX" "$CONSUMER"; do
    (cd "$repo" && git for-each-ref --sort=-committerdate refs/remotes/origin \
      --format="$(basename "$repo")	%(refname:lstrip=3)	%(objectname:short)	%(committerdate:iso-strict)	%(subject)")
  done
} > "$OUT/remote-branches.tsv"

# 3. TASKs: conteo por estado (store versionado, lectura mode=ro) y claims vivos del ledger.
cd "$THYROX"
python3 - "$OUT" <<'EOF'
import json, sqlite3, sys, collections
out = sys.argv[1]
c = sqlite3.connect("file:agent-results/agent_store.sqlite3?mode=ro", uri=True)
rows = c.execute("select coalesce(layer_citation_id, citation_id), status, coalesce(owner,''), updated_at, replace(subject, char(9), ' ') from tasks").fetchall()
with open(f"{out}/tasks-by-status.tsv", "w") as f:
    f.write("status\tcount\n")
    for k, v in sorted(collections.Counter(r[1] for r in rows).items()):
        f.write(f"{k}\t{v}\n")
with open(f"{out}/tasks-open.tsv", "w") as f:
    f.write("citation\tstatus\towner\tupdated_at\tsubject\n")
    for r in sorted((r for r in rows if r[1] != "completed"), key=lambda r: r[3] or "", reverse=True):
        f.write("\t".join(str(x) for x in r) + "\n")
# Un claim vive mientras no lo siga un release del mismo id.
live = {}
for line in open(".claude/coordination/claims.jsonl"):
    e = json.loads(line)
    if e.get("op") == "claim":
        live[e["id"]] = e
    elif e.get("op") in ("release", "unclaim"):
        live.pop(e.get("id") or e.get("claim"), None)
with open(f"{out}/claims-live.tsv", "w") as f:
    f.write("claim\towner\tbranch\ttask\tpath\tat\n")
    for e in live.values():
        f.write("\t".join(str(e.get(k, "")) for k in ("id", "owner", "branch", "task", "path", "at")) + "\n")
EOF

# 4. Trabajos del ledger y procesos de thyrox/consumidor vivos.
bash bin/wait-jobs status > "$OUT/jobs-ledger.txt" 2>&1
ps -eo pid,ppid,lstart,etime,pcpu,rss,args --sort=pid \
  | grep -E 'llama|ollama|thyrox|translat|wait-jobs|bg\.sh|headless|coordinator|podman|conmon' \
  | grep -v grep > "$OUT/processes.txt"

# 5. Podman: versión, almacenamiento, imágenes (con las sin etiqueta), contenedores, volúmenes, pods.
podman version --format '{{.Client.Version}}' > "$OUT/podman-version.txt" 2>&1
podman info --format '{{.Store.GraphDriverName}}	{{.Store.GraphRoot}}' >> "$OUT/podman-version.txt" 2>&1
podman images --all --no-trunc --format '{{.ID}}	{{.Repository}}	{{.Tag}}	{{.Digest}}	{{.Size}}	{{.CreatedAt}}' > "$OUT/podman-images.tsv" 2>&1
podman inspect --type image $(podman images --all -q) --format '{{.Id}}	{{join .RepoDigests ","}}' > "$OUT/podman-image-repodigests.tsv" 2>&1
podman ps --all --format '{{.ID}}	{{.Names}}	{{.State}}	{{.Image}}	{{.Labels}}' > "$OUT/podman-containers.tsv" 2>&1
podman volume ls --format '{{.Name}}	{{.Driver}}	{{.Mountpoint}}' > "$OUT/podman-volumes.tsv" 2>&1
podman pod ls --format '{{.ID}}	{{.Name}}	{{.Status}}' > "$OUT/podman-pods.tsv" 2>&1

# 6. Modelos y datasets locales: catálogo, ubicaciones, cualificaciones (copias por referencia).
for f in catalog.json artifact-locations.json qualifications.json; do
  [[ -f ".thyrox/models/$f" ]] && sha256sum ".thyrox/models/$f"
done > "$OUT/model-registry-files.sha256"
find .thyrox/models/artifacts .thyrox/datasets -maxdepth 2 -type f -printf '%s\t%p\n' 2>/dev/null > "$OUT/local-artifacts.tsv"

# 7. Almacenes: agent_store (versionado), ledger de claims, colas y estado del runtime.
{
  printf 'store\tpath\tbytes\tsha256\tversioned\n'
  for p in agent-results/agent_store.sqlite3 .claude/coordination/claims.jsonl; do
    v=no; git ls-files --error-unmatch "$p" >/dev/null 2>&1 && v=yes
    printf '%s\t%s\t%s\t%s\t%s\n' "$(basename "$p")" "$p" "$(stat -c %s "$p")" "$(sha256sum "$p" | cut -d' ' -f1)" "$v"
  done
} > "$OUT/stores.tsv"
du -s --block-size=1 .thyrox/runtime/* 2>/dev/null > "$OUT/runtime-state-sizes.tsv"
df -B1 / | tail -1 > "$OUT/disk.txt"
free -b | sed -n 2p >> "$OUT/disk.txt"
echo "discover: inventarios en $OUT"
