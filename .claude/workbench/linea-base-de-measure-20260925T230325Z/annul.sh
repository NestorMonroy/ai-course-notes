#!/usr/bin/env bash
# Anulaciones de la línea base de `measure`: patrón y reemplazo por ENVIRON.
set -u
cd /home/user/ai-course-notes
B="$1"; F=tools/scripts/translation_loop.py
cp "$F" "$B/orig.py"
sub1() { PAT="$1" REP="$2" gawk -i inplace '{ if (index($0, ENVIRON["PAT"])) { n++; print ENVIRON["REP"]; next } print } END { if (n != 1) exit 9 }' "$F"; }
run() {
    uv run --locked pytest tests/test_translation_loop.py -q -p no:cacheprovider > "$B/annul-$1.txt" 2>&1
    echo "$1: $(grep -E '^FAILED' "$B/annul-$1.txt" | sed 's/ - .*//' | tr '\n' ' ') | $(grep -m1 -E '^>' "$B/annul-$1.txt" | cut -c1-110) | $(tail -1 "$B/annul-$1.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
cp "$B/orig.py" "$F"
sub1 '    if not previous:' '    if False:' && sub1 '    before_rows = read_jsonl(previous[-1])' '    before_rows = read_jsonl(previous[-1]) if previous else latest_signals(root)' && run I-sin-linea-base || echo "I: el patrón no casa" >> "$B/annul-summary.txt"
cp "$B/orig.py" "$F"
sub1 '    before_rows = read_jsonl(previous[-1])' '    before_rows = latest_signals(root)' && run C-sin-medicion-anterior || echo "C: el patrón no casa" >> "$B/annul-summary.txt"
cp "$B/orig.py" "$F"; rm "$B/orig.py"
echo "EXIT=0" >> "$B/annul-summary.txt"
