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
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-summary.txt"; return; }
    uv run --locked pytest tests/test_translation_loop.py -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//' | tr '\n' ' ') | $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
annul A-sin-clave-de-causa '    signal, detail = row["signal"], row.get("detail") or ""' '    return row["signal"]'
annul B-sin-normalizar-han '            return f"{signal}:han" if HAN.fullmatch' '            return f"{signal}:U+{glyph.group(\x27code\x27)}"'
annul C-sin-medicion-anterior '    before_rows = read_jsonl(previous[-1]) if previous else latest_signals(root)' '    before_rows = latest_signals(root)'
cp "$B/translation_loop.py.orig" "$F"
rm "$B/translation_loop.py.orig"
echo "EXIT=0" >> "$B/annul-summary.txt"
