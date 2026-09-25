#!/usr/bin/env bash
# Sonda de los hallazgos H-THYROX-176 a 178: un consumidor cuyo nombre de clon NO lleva el
# prefijo `kaupamex-` (aqui, ai-course-notes). Solo lectura salvo el `mkdir`
# del hogar por defecto de `workbench_dir()`, que se ejercita en un directorio
# temporal. Vive en el banco del CONSUMER (ai-course-notes); la raiz de thyrox
# sale de su `.env` por `tools/thyrox/lib.sh`, no de la ubicacion del guion.
set -uo pipefail
CONSUMER="$(cd "$(dirname "$0")/../../../.." && pwd)"
source "$CONSUMER/tools/thyrox/lib.sh"
thyrox_prepare_env || exit $?
T="$THYROX_ROOT"
P="$T/.venv/bin/python"
export PYTHONPATH="$T/src"
TMP="$(mktemp -d)"; C="$TMP/ai-course-notes"; mkdir -p "$C"; git -C "$C" init -q
for v in $(env | grep -o '^THYROX_[A-Z_]*'); do unset "$v"; done
q="from pathlib import Path; import workbench.paths as w; print(w.workbench_dir(Path('$C')))"

echo "## 1 — la familia por clon ignora la clave del consumidor"
for kv in THYROX_WORKBENCH_AI_COURSE_NOTES=/declarado/full THYROX_WORKBENCH_NOTES=/declarado/suffix THYROX_WORKBENCH_DIR=/declarado/global; do
    echo "$kv -> $(env "$kv" timeout 30 "$P" -c "$q" 2>&1 | tail -1)"
done
timeout 30 "$P" -c "
from pathlib import Path; import workbench.paths as w, paths.reach as r
c=Path('$C')
print('repo_of              ->', w.repo_of(c))
print('clone_suffix_of      ->', r.clone_suffix_of(c))
print('workbench_home_name  ->', w.workbench_home_name('ai-course-notes'))"

echo "## 2 — la raiz se compone con un prefijo que el clon no lleva"
# El arbol se redirige a TMP con THYROX_REACH_ROOT: declarations.py CREA los
# hogares que compone, y fuera de TMP dejaria directorios fantasma en el host.
R="$TMP/reach"; mkdir -p "$R"
d() { (cd "$T" && THYROX_REACH_ROOT="$R" timeout 60 "$P" src/paths/declarations.py "$@" 2>&1); }
echo "a) sin THYROX_REACH_ROOTS -> $(d | tail -1)"
echo "b) con THYROX_REACH_ROOTS=ai-course-notes,thyrox:"
(export THYROX_REACH_ROOTS=ai-course-notes,thyrox; d | grep -E '^->' | head -4)
echo "c) directorios que (b) creo bajo el arbol:"
(cd "$R" && find . -mindepth 1 -maxdepth 3 -type d | sort)
echo "d) de nuevo sin THYROX_REACH_ROOTS -> $(d | head -1)"
echo "e) hallazgo_ids acunar THYROX --consumer thyrox -> $(cd "$T" && THYROX_REACH_ROOT="$R" timeout 60 "$P" src/hallazgo/hallazgo_ids.py acunar THYROX --consumer thyrox 2>&1 | tail -1)"
echo "## 3 — un CLI sin punto de partida no lee el .env del consumidor"
printf 'THYROX_AGENT_STORE=%s\n' "$C/agent-results/agent_store.sqlite3" > "$C/.env"
q="import paths.reach as r; print(r.agent_store_path(create=False))"
echo "cwd=consumidor, sin THYROX_ENV_FILE -> $(cd "$C" && timeout 30 "$P" -c "$q" 2>&1 | tail -1)"
echo "cwd=consumidor, con THYROX_ENV_FILE -> $(cd "$C" && THYROX_ENV_FILE="$C/.env" timeout 30 "$P" -c "$q" 2>&1 | tail -1)"
echo "reach con start=consumidor          -> $(timeout 30 "$P" -c "from pathlib import Path; import paths.reach as r; print(r.agent_store_path(Path('$C'), create=False))" 2>&1 | tail -1)"
rm -rf "$TMP"
