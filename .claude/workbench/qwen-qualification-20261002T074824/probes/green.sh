#!/usr/bin/env bash
# Verde: el guion en su sitio, sus pruebas y las del ciclo.
set -u
B=/home/user/ai-course-notes/.claude/workbench/qwen-qualification-20261002T074824
cd /home/user/ai-course-notes
cp "$B/probes/qualification_suite.py" tools/scripts/qualification_suite.py
uv run --quiet pytest -q tests/test_qualification_suite.py > "$B/outputs/green.txt" 2>&1; echo "suite exit=$? $(tail -1 "$B/outputs/green.txt")"
