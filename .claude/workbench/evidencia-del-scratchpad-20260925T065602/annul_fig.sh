set -u
cd /home/user/ai-course-notes
F=tools/scripts/render_zhangxiaojun_concept_figures.py; cp $F /tmp/F.bak
T=tests/test_concept_figures.py
r(){ uv run --locked pytest -q $T 2>&1 | grep -E "^FAILED|passed|failed"; cp /tmp/F.bak $F; }
echo "== sin espacio latino"; sed -i 's/    LATIN_SPACING = lang != "zh"/    LATIN_SPACING = False/' $F; r
echo "== sin ajuste de tamano"; sed -i 's/    while size > floor and/    while False and/' $F; r
echo "== sin rechazo por faltante"; sed -i 's/        if missing:$/        if False:/' $F; r
echo "== sin nombre hermano"; sed -i 's/    return rel if LANG == "zh" else/    return rel if True else/' $F; r
echo "== restaurado"; git diff --quiet $F 2>/dev/null; uv run --locked pytest -q $T 2>&1 | tail -1
