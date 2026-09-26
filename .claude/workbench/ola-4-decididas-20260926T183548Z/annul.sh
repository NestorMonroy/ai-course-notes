#!/usr/bin/env bash
# Anulación de las tres mitades de la ola 4: patrón y reemplazo por ENVIRON.
set -u
cd /home/user/ai-course-notes
B="$1"
annul() {  # nombre, archivo, suite, patrón, reemplazo
    local name="$1" file="$2" suite="$3"
    cp "$file" "$B/orig"
    PAT="$4" REP="$5" gawk -i inplace '{ if (index($0, ENVIRON["PAT"])) { n++; print ENVIRON["REP"]; next } print } END { if (n != 1) exit 9 }' "$file" \
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-summary.txt"; cp "$B/orig" "$file"; return; }
    PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest "$suite" -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    cp "$B/orig" "$file"
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//;s/.*:://' | tr '\n' ' ')| $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
P=tools/scripts/check_prose_vocabulary.py
annul R1-sin-nombre-propio "$P" tests/test_prose_vocabulary.py \
    '            named = raw[0].isupper() and before and before[-1] not in ".!?¿¡:«\"\n{"' '            named = False'
annul R2-sin-unidad "$P" tests/test_prose_vocabulary.py \
    '            unit = re.search(r"\d$", before) is not None' '            unit = False'
annul R3-sin-causa-decidida tools/scripts/translation_loop.py tests/test_translation_loop.py \
    '        elif decided(key, names[key]):' '        elif False:'
rm -f "$B/orig"
echo "EXIT=0" >> "$B/annul-summary.txt"
