#!/usr/bin/env bash
# Rojo: la prueba existe y el guion no.
set -u
B=/home/user/ai-course-notes/.claude/workbench/qwen-qualification-20261002T074824
cd /home/user/ai-course-notes
cp "$B/probes/test_qualification_suite.py" tests/test_qualification_suite.py
uv run --quiet pytest -q tests/test_qualification_suite.py > "$B/outputs/red.txt" 2>&1; echo "exit=$?"; tail -3 "$B/outputs/red.txt"
