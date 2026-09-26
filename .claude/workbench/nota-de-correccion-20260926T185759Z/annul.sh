#!/usr/bin/env bash
# Anulación de las tres mitades de la nota de corrección: patrón y reemplazo por ENVIRON.
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
L=tools/scripts/translation_loop.py; T=tests/test_translation_loop.py
annul S1-sin-nota "$L" "$T" '    write_corrections(units, failed)' '    pass'
annul S2-sin-forma-adoptada "$L" "$T" '            target = targets.get(word.lower())' '            target = None'
annul S3-sin-instruccion tools/lang/es-mx/translator_prompt.md "$T" '1. Lee el fragmento con `Read`. Si junto a él existe `NNN.correccion.md` (el' '1. Lee el fragmento con `Read`.'
annul M1-sin-memoria "$L" "$T" '            if len(fields) >= 4:' '            if False:'
rm -f "$B/orig"
echo "EXIT=0" >> "$B/annul-summary.txt"
