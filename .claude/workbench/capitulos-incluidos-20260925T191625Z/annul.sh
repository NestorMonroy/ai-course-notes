#!/usr/bin/env bash
# Anulación de cada mitad de los capítulos incluidos: se retira, se corre la
# suite derivada y se restaura. Patrón y reemplazo van por ENVIRON: `-v`
# procesa escapes y `\\` llegaría como `\`.
set -u
cd /home/user/ai-course-notes
B="$1"
F=tools/scripts/translation_loop.py
cp "$F" "$B/translation_loop.py.orig"
annul() {
    local name="$1"
    cp "$B/translation_loop.py.orig" "$F"
    PAT="$2" REP="$3" gawk -i inplace '{ if (index($0, ENVIRON["PAT"])) { n++; print ENVIRON["REP"]; next } print } END { if (n != 1) exit 9 }' "$F" \
        || { echo "$name: el patrón no casa una sola vez" >> "$B/annul-summary.txt"; return; }
    uv run --locked pytest tests/test_translation_loop.py -q -p no:cacheprovider > "$B/annul-$name.txt" 2>&1
    echo "$name: $(grep -E '^FAILED' "$B/annul-$name.txt" | sed 's/ - .*//' | tr '\n' ' ') | $(grep -E '^E +assert' "$B/annul-$name.txt" | head -1 | cut -c1-120) | $(tail -1 "$B/annul-$name.txt")" >> "$B/annul-summary.txt"
}
: > "$B/annul-summary.txt"
annul E-sin-seguir-inputs '        queue += [(child, base) for child in included_files(original, base)]' '        pass'
annul F-sin-mapear-ifFileExists '    return re.sub(r"\\IfFileExists\{([^}]+?)(?<!\.es-mx)\.tex\}",' '    return text if True else re.sub(r"\\IfFileExists\{([^}]+?)(?<!\.es-mx)\.tex\}",'
annul G-compilar-capitulos '        if compile_ and "\\documentclass" in es_text:' '        if compile_:'
annul H-localizar-capitulos '        text = map_inputs(localize(original) if "\\documentclass" in original else original)' '        text = map_inputs(localize(original))'
cp "$B/translation_loop.py.orig" "$F"
rm "$B/translation_loop.py.orig"
echo "EXIT=0" >> "$B/annul-summary.txt"
