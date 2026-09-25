#!/usr/bin/env bash
# Anulación de cada mitad nueva: se retira, se corre la suite derivada y se restaura.
set -u
cd /home/user/ai-course-notes
B="$1"
F=tools/scripts/translation_loop.py
cp "$F" "$B/translation_loop.py.orig"
annul() {  # nombre, patrón, reemplazo (gawk gensub sobre una línea única)
    local name="$1" pattern="$2" replacement="$3"
    cp "$B/translation_loop.py.orig" "$F"
    gawk -i inplace -v p="$pattern" -v r="$replacement" '{ if (index($0, p)) { n++; sub(/.*/, r) } print } END { if (n != 1) exit 9 }' "$F" \
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-2-summary.txt"; return; }
    uv run --locked pytest tests/test_translation_loop.py -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//' | tr '\n' ' ') | $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-2-summary.txt"
}
: > "$B/annul-2-summary.txt"
annul C-sin-medicion-anterior '    before_rows = read_jsonl(previous[-1]) if previous else latest_signals(root)' '    before_rows = latest_signals(root)'
annul D-sin-gate-de-neto-negativo '    if len(introduced) > len(resolved):' '    if False:'
cp "$B/translation_loop.py.orig" "$F"
rm "$B/translation_loop.py.orig"
echo "EXIT=0" >> "$B/annul-2-summary.txt"
