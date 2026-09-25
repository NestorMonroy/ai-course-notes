set -u
cd /home/user/ai-course-notes
L=tools/scripts/translation_loop.py; cp $L /tmp/L3.bak
r(){ uv run --locked pytest -q tests/test_translation_loop.py 2>&1 | grep -E "^FAILED|passed|failed"; cp /tmp/L3.bak $L; }
echo "== sin marcadores"; sed -i 's/    return match.group(1) + "\\n" if match else None/    return match.group(1) + "\\n" if match else result/' $L; r
echo "== sin copia de fragmento sin chino"; sed -i 's/    plain = \[row for row in pending if not HAN.search/    plain = [row for row in [] if not HAN.search/' $L; r
echo "== sin memfree"; sed -i 's/, "--memfree", args.memfree,/,/' $L; r
echo "== componentes cruzados"; sed -i 's/"cache_read": "cache_read_input_tokens", "output"/"cache_read": "cache_creation_input_tokens", "output"/' $L; r
echo "== restaurado"; uv run --locked pytest -q tests/test_translation_loop.py 2>&1 | tail -1
