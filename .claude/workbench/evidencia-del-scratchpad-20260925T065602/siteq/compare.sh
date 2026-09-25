#!/usr/bin/env bash
# Equivalencia zh del sitio: generador de HEAD contra el de --lang, sobre 11 notas reales.
set -uo pipefail
PY=/home/user/ai-course-notes/.venv/bin/python
cd /tmp/claude-0/-home-user/81a17524-87b5-5e9d-997b-0732e892d302/scratchpad/siteq
$PY old/generate_site.py --root root --output out-old --skip-tikz --no-compress-images --strict > old.log 2>&1; echo "old exit=$?"
$PY /home/user/ai-course-notes/tools/web/generate_site.py --root root --output out-new --skip-tikz --no-compress-images --strict > new.log 2>&1; echo "new exit=$?"
echo "paginas: old=$(find out-old/docs -name '*.md' | wc -l) new=$(find out-new/docs -name '*.md' | wc -l)"
if diff -r out-old out-new > diff.txt; then echo "SITIO zh IDENTICO ($(find out-new -type f | wc -l) archivos)"; else echo "DIFIERE"; head -30 diff.txt; fi
