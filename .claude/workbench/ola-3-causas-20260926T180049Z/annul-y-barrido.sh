#!/usr/bin/env bash
# Anulación de las cuatro mitades de la ola 3 y, después, el barrido real.
set -u
cd /home/user/ai-course-notes
B="$1"
annul() {  # nombre, archivo, suite, patrón, reemplazo (patrón y reemplazo por ENVIRON)
    local name="$1" file="$2" suite="$3"
    cp "$file" "$B/orig"
    PAT="$4" REP="$5" gawk -i inplace '{ if (index($0, ENVIRON["PAT"])) { n++; print ENVIRON["REP"]; next } print } END { if (n != 1) exit 9 }' "$file" \
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-summary.txt"; cp "$B/orig" "$file"; return; }
    PYTHONDONTWRITEBYTECODE=1 uv run --locked pytest "$suite" -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    cp "$B/orig" "$file"
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//;s/.*:://' | tr '\n' ' ')| $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
L=tools/scripts/translation_loop.py; T=tests/test_translation_loop.py
annul Q1-sin-respaldo-cjk tools/scripts/localize_preamble.py tests/test_localize_preamble.py \
    '    "\\setCJKfallbackfamilyfont{\\CJKrmdefault}{WenQuanYi Zen Hei}\n"' '    ""'
annul Q2-sin-rechazo-fffd "$L" "$T" '    if "�" in es and "�" not in zh:' '    if False:'
annul Q3-sin-clave-de-residuo "$L" "$T" '    if signal == "parity:residual-han":' '    if False:'
annul Q4-barrido-solo-notes "$L" "$T" '    notes = translated_notes(root)' \
    '    notes = sorted(p.resolve() for p in root.rglob("*-notes.es-mx.tex") if not SKIPPED_DIRS & set(p.relative_to(root).parts))'
rm -f "$B/orig"
echo "== barrido real" >> "$B/annul-summary.txt"
python3 "$L" sweep --bench "$B" --iteration 7 > "$B/barrido-7.log" 2>&1; echo "sweep=$?" >> "$B/annul-summary.txt"
echo "sin respaldo: $(git ls-files '*.es-mx.tex' | xargs grep -l 'usepackage{xeCJK}' | wc -l)" >> "$B/annul-summary.txt"
echo "EXIT=0" >> "$B/annul-summary.txt"
