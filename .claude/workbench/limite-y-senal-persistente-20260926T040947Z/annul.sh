#!/usr/bin/env bash
# Anulación de cada mitad del límite de sesión: patrón y reemplazo por ENVIRON.
set -u
cd /home/user/ai-course-notes
B="$1"
annul() {  # nombre, archivo, patrón, reemplazo
    local name="$1" file="$2"
    cp "$file" "$B/orig"
    PAT="$3" REP="$4" gawk -i inplace '{ if (index($0, ENVIRON["PAT"])) { n++; print ENVIRON["REP"]; next } print } END { if (n != 1) exit 9 }' "$file" \
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-summary.txt"; cp "$B/orig" "$file"; return; }
    uv run --locked pytest tests/test_translation_loop.py -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    cp "$B/orig" "$file"
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//;s/.*:://' | tr '\n' ' ')| $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
L=tools/scripts/translation_loop.py; W=tools/scripts/translate_wave.sh
annul L1-translate-no-detecta "$L" '    if limit:' '    if False:'
annul L2-cycle-ignora-el-5 "$L" '    if translated == 5:' '    if False:'
annul L3-advance-reintenta "$L" '        if code in (0, 2, 5):' '        if code in (0, 2):'
annul L4-ola-sin-marca "$W" '    (( code == 5 )) && : > "$WAVE/limite"' '    true'
rm -f "$B/orig"
echo "EXIT=0" >> "$B/annul-summary.txt"
