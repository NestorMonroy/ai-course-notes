#!/usr/bin/env bash
# Espera las anulaciones S1-S3/M1, guarda su código y corre la ola 6 sin
# vigilancia turno a turno (plan 9.1): una notificación al final, no N turnos.
set -u
cd /home/user/ai-course-notes
N=$(ls -d .claude/workbench/nota-de-correccion-*)
while pgrep -f '[n]ota-de-correccion.*annul.sh' >/dev/null; do sleep 20; done
eval "$(tools/thyrox/run commit_identity env)"
P=(tools/scripts/translation_loop.py tools/lang/es-mx/translator_prompt.md tests/test_translation_loop.py "$N")
git add -N -- "${P[@]}"
git commit -q -F - -- "${P[@]}" <<'MSG'
Tell each retranslated chunk what failed in it

In wave 5, «antropomorfización», «la clave está en» and
«ortogonalización» came back after retranslation: the model only got
the general template and never learned what had failed in that chunk.
retranslate now leaves NNN.correccion.md next to each chunk it sends
back, naming each defect and, for a glossary-rejected word, the form
the glossary adopts; the template tells the model to read it.

usage also records the peak memory, wall and CPU time that GNU Time
leaves in <n>.time for each claude -p, with «-» where nothing was
measured. The annulment summary is in the correction bench.
MSG
git push -q origin feature/es-mx-translation
L=.claude/cache/ola/ola-6-$(date -u +%Y%m%dT%H%M%SZ).log
bash tools/scripts/translate_wave.sh --from 10 --to 25 --jobs 4 --model claude-sonnet-5 --compile > "$L" 2>&1
echo "EXIT=$?" >> "$L"
mapfile -t R < <(git status --short --untracked-files=all | gawk '{print $2}')
git add -N -- "${R[@]}"
git commit -q -m "Record wave 6 over plan rows 10 to 25" -m "First wave with GNU Time installed: each iteration's usage.tsv carries
the peak memory of every claude -p. Results are read in the next commit." -- "${R[@]}"
git push -q origin feature/es-mx-translation
echo "== $(git log -1 --format='%h %s')"
grep -E "translate_wave" "$L" | tail -3
