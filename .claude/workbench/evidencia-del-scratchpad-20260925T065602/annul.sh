set -u
cd /home/user/ai-course-notes
L=tools/scripts/translation_loop.py; P=tools/scripts/check_prose_vocabulary.py
cp $L /tmp/L.bak; cp $P /tmp/P.bak
T="tests/test_translation_loop.py tests/test_prose_vocabulary.py"
echo "== sin filtro de deuda heredada"
sed -i 's/if key not in inherited\]/]/' $L
uv run --locked pytest -q $T 2>&1 | grep -E "^FAILED|passed|failed"
cp /tmp/L.bak $L
echo "== sin forma adoptada del glosario"
sed -i 's/ and word not in keep and not attested/ and not attested/' $P
uv run --locked pytest -q $T 2>&1 | grep -E "^FAILED|passed|failed"
cp /tmp/P.bak $P
echo "== restaurado"
git diff --stat
uv run --locked pytest -q $T 2>&1 | tail -1
