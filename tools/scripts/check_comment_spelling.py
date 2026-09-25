#!/usr/bin/env python3
"""Tildes y eñes en los comentarios, docstrings y textos en español del repositorio.

    check_comment_spelling.py [--fix] <archivo>...

Los identificadores van en inglés y los comentarios en español; el español sin
tildes ni eñe (`traduccion`, `espanol`, `senal`) es un defecto, no una variante.
Se revisan solo los tramos que son texto:

- `.py`: los comentarios `#` y las docstrings (no las demás cadenas ni el código);
- `.sh`: los comentarios `#` fuera de comillas (no la línea `#!`);
- `.md`: todo el texto salvo los bloques y los tramos de código.

Una palabra se reporta cuando el diccionario es_MX la rechaza y acepta su forma
con tildes o eñe (el eje `unaccented` de `check_prose_vocabulary.py`). Con
`--fix` se sustituye esa forma solo dentro del tramo. Las formas prohibidas
(`prohibited_forms.txt`) también se reportan, pero no se corrigen solas.
Sale 1 si quedan hallazgos.
"""
from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_prose_vocabulary as prose  # noqa: E402

WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
SH_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
SH_COMMENT = re.compile(r"(?:^|(?<=\s))#(?!!)")
# Una forma entre `…` o «…» se cita (para prohibirla, para mostrarla), no se usa.
CITATION = re.compile(r"`[^`]*`|«[^»]*»")

Span = tuple[int, int, int]  # línea (desde 1), columna inicial, columna final

# Homógrafos que el diccionario acepta porque son palabras válidas con otro
# sentido (`ingles`, plural de ingle; `termino`, del verbo terminar). Medido en
# la rama: 15 `ingles` y 17 `termino`, siempre por «inglés» y «término».
HOMOGRAPHS = {"ingles": "inglés", "termino": "término"}

# El idioma del tramo se decide por sus palabras funcionales: una regla de
# ortografía del español solo aplica a un tramo escrito en español. Medido en
# el barrido de la rama: `AGENTS.md` está en inglés y el gate le proponía
# `names → ñames` y `version → versión`.
SPANISH_FUNCTION = {"de", "la", "el", "que", "los", "las", "en", "y", "del", "se", "por", "con", "para",
                    "una", "un", "es", "no", "lo", "al", "su", "sus", "como", "pero", "sin", "sobre", "si",
                    "cuando", "donde", "porque", "más", "ya", "este", "esta", "estos", "estas", "entre",
                    "hasta", "desde", "cada", "otro", "otra", "también", "sólo", "solo", "muy", "le", "les"}
ENGLISH_FUNCTION = {"the", "of", "and", "to", "in", "is", "for", "with", "that", "this", "it", "on", "as",
                    "are", "be", "or", "by", "from", "an", "not", "if", "when", "into", "than", "them",
                    "they", "their", "we", "you", "your", "only", "all", "each", "but", "so", "at", "do",
                    "does", "can", "will", "has", "have", "was", "were", "which", "there", "where", "how",
                    "what", "its", "these", "those", "such", "may", "must", "should", "then", "also"}
SENTENCE_START = set(".:;!?¿¡|#*-(")


def span_language(text: str) -> str | None:
    """`es`, `en` o `None` si el tramo no trae palabras funcionales.

    Se cuentan tokens separados por espacios: el `in` de `opt-in` no cuenta.
    """
    words = [t.strip(".,;:()«»`'\"").lower() for t in text.split()]
    es = sum(w in SPANISH_FUNCTION for w in words)
    en = sum(w in ENGLISH_FUNCTION for w in words)
    if es == en == 0:
        return None
    return "en" if en > es else "es"


def document_language(spans: list[str]) -> str:
    """El idioma del documento: decide los tramos sin palabras funcionales."""
    langs = [span_language(t) for t in spans]
    return "en" if langs.count("en") > langs.count("es") else "es"


def is_proper_name(text: str, start: int, word: str) -> bool:
    """`Debian`, `LaTeX`: mayúscula que no abre oración, o mayúsculas internas."""
    if any(ch.isupper() for ch in word[1:]):
        return True
    if not word[:1].isupper():
        return False
    before = text[:start].rstrip()
    return bool(before) and before[-1] not in SENTENCE_START


def python_spans(text: str) -> list[Span]:
    lines = text.splitlines()
    spans: list[Span] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            spans.append((tok.start[0], tok.start[1], tok.end[1]))
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                for n in range(first.lineno, first.end_lineno + 1):
                    spans.append((n, 0, len(lines[n - 1])))
    return spans


def shell_spans(text: str) -> list[Span]:
    spans = []
    for n, line in enumerate(text.splitlines(), 1):
        if n == 1 and line.startswith("#!"):
            continue
        blank = SH_QUOTED.sub(lambda m: " " * len(m.group(0)), line)
        match = SH_COMMENT.search(blank)
        if match:
            spans.append((n, match.start(), len(line)))
    return spans


def markdown_spans(text: str) -> list[Span]:
    spans, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            spans.append((n, 0, len(line)))
    return spans


def spans_of(path: Path, text: str) -> list[Span]:
    if path.suffix == ".py":
        return python_spans(text)
    if path.suffix == ".sh":
        return shell_spans(text)
    if path.suffix == ".md":
        return markdown_spans(text)
    return []


def span_text(line: str, start: int, end: int, markdown: bool) -> str:
    """El tramo con las citas en blanco, del mismo largo para no mover columnas."""
    return CITATION.sub(lambda m: " " * len(m.group(0)), line[start:end])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    es, _en = prose.load_lexicons()
    accented = {**prose.accented_forms(es), **HOMOGRAPHS}
    texts = {p: p.read_text(encoding="utf-8") for p in args.files}
    found: dict[Path, list[tuple[int, int, int, str, str]]] = {}
    words: set[str] = set()
    for path, text in texts.items():
        lines = text.splitlines()
        spans = [(n, span_text(lines[n - 1], a, b, path.suffix == ".md"), a) for n, a, b in spans_of(path, text)]
        document = document_language([c for _n, c, _a in spans])
        for n, chunk, start in spans:
            language = span_language(chunk)
            if (language or document) != "es":
                continue
            for m in WORD.finditer(chunk):
                low = m.group(0).lower()
                if low in accented and not is_proper_name(chunk, m.start(), m.group(0)):
                    found.setdefault(path, []).append((n, start + m.start(), start + m.end(), m.group(0), low))
                    words.update({low, accented[low]})
    dictionary = prose.SpanishDictionary(words)
    remaining = 0
    # Las formas prohibidas (`prohibited_forms.txt` y las rechazadas del
    # glosario) se reportan y no se corrigen solas: `corrida` puede ser
    # «ejecución» o «iteración», y elegir es juicio.
    _keep, rejected = prose.load_glossary(prose.DEFAULT_GLOSSARY)
    forbidden = [(form, sub, re.compile(rf"(?<![\w-]){re.escape(form)}(?![\w-])", re.I))
                 for form, sub in prose.load_forbidden(prose.DEFAULT_FORBIDDEN) + rejected]
    for path, text in texts.items():
        lines = text.splitlines()
        for n, start, end in spans_of(path, text):
            chunk = span_text(lines[n - 1], start, end, path.suffix == ".md")
            if (span_language(chunk) or document_language([span_text(l, 0, len(l), False) for l in lines])) != "es":
                continue
            for form, sub, pattern in forbidden:
                if pattern.search(chunk):
                    print(f"{path}:{n}: {form} (prohibida)" + (f" → {sub}" if sub else ""))
                    remaining += 1
    for path, hits in found.items():
        hits = [h for h in hits if h[4] in HOMOGRAPHS
                or (not dictionary.accepts(h[4]) and dictionary.accepts(accented[h[4]]))]
        if not args.fix:
            for n, _s, _e, raw, low in hits:
                print(f"{path}:{n}: {raw} → {cased(accented[low], raw)}")
            remaining += len(hits)
            continue
        lines = texts[path].split("\n")
        for n, s, e, raw, low in sorted(hits, key=lambda h: (h[0], -h[1])):
            line = lines[n - 1]
            lines[n - 1] = line[:s] + cased(accented[low], raw) + line[e:]
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{path}: {len(hits)} corrección(es)")
    if not args.fix:
        print(f"check_comment_spelling: {remaining} palabra(s) sin tildes o eñe en {len(args.files)} archivo(s)",
              file=sys.stderr)
    return 1 if remaining else 0


def cased(form: str, like: str) -> str:
    """La forma corregida con la capitalización de la original."""
    if like.isupper():
        return form.upper()
    return form[:1].upper() + form[1:] if like[:1].isupper() else form


if __name__ == "__main__":
    sys.exit(main())
