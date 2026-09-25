#!/usr/bin/env bash
# Controles de anulación de los ejes de prosa con hunspell: se retira cada
# guarda y tienen que caer exactamente las pruebas que dependen de ella.
set -u
cd /home/user/ai-course-notes
P=tools/scripts/check_prose_vocabulary.py; C=.claude/cache/annul; mkdir -p "$C"; cp "$P" "$C/cpv.py"
T="tests/test_prose_vocabulary.py tests/test_translation_loop.py"
r() { uv run --locked pytest -q $T 2>&1 | grep -E "^FAILED|passed|failed"; cp "$C/cpv.py" "$P"; }
echo "== sin eje de tildes"; sed -i 's/            if word in accented and not dictionary.accepts(word) and dictionary.accepts(accented\[word\]):/            if False:/' "$P"; r
echo "== spanglish sin diccionario"; sed -i 's/            elif not dictionary.accepts(word) and is_spanglish(/            elif is_spanglish(/' "$P"; r
echo "== inglés sin diccionario"; sed -i 's/                  and not dictionary.accepts(word) and is_english(word, es, en)):/                  and is_english(word, es, en)):/' "$P"; r
echo "== sin filtro de basura del léxico"; sed -i 's/            if len(word) < ACCENT_MIN_LENGTH or not SPANISH_WORD.fullmatch(word):/            if False:/' "$P"; r
echo "== restaurado"; git diff --quiet -- "$P" && echo "sin cambios fuera de lo esperado" || git diff --stat -- "$P"
