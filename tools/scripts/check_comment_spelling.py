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
`--fix` se sustituye esa forma solo dentro del tramo. Sale 1 si quedan hallazgos.
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
MD_INLINE_CODE = re.compile(r"`[^`]*`")

Span = tuple[int, int, int]  # línea (desde 1), columna inicial, columna final


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
    chunk = line[start:end]
    return MD_INLINE_CODE.sub(lambda m: " " * len(m.group(0)), chunk) if markdown else chunk


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    es, _en = prose.load_lexicons()
    accented = prose.accented_forms(es)
    texts = {p: p.read_text(encoding="utf-8") for p in args.files}
    found: dict[Path, list[tuple[int, int, int, str, str]]] = {}
    words: set[str] = set()
    for path, text in texts.items():
        lines = text.splitlines()
        for n, start, end in spans_of(path, text):
            for m in WORD.finditer(span_text(lines[n - 1], start, end, path.suffix == ".md")):
                low = m.group(0).lower()
                if low in accented:
                    found.setdefault(path, []).append((n, start + m.start(), start + m.end(), m.group(0), low))
                    words.update({low, accented[low]})
    dictionary = prose.SpanishDictionary(words)
    remaining = 0
    for path, hits in found.items():
        hits = [h for h in hits if not dictionary.accepts(h[4]) and dictionary.accepts(accented[h[4]])]
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
