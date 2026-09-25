#!/usr/bin/env python3
"""Paridad estructural entre una nota zh y su traducción es-MX (V1-V3 del plan).

    check_translation_parity.py <nota.tex> <nota.es-mx.tex> [--glossary TSV]

Imprime una señal por linea, `parity:<clave>\\t<detalle>`, y sale 1 si hay
alguna, 0 si no. La señal es estable: es la que registra la memoria de
patrones y la que busca el barrido (`docs/ES_MX_TRANSLATION_PLAN.md`).

Mide la forma. Una traducción con la misma estructura y otro sentido pasa.
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOSSARY = REPO_ROOT / "tools" / "lang" / "es-mx" / "glossary.tsv"
HAN = re.compile(r"[\u4e00-\u9fff]")
# Un original chino entre paréntesis es legitimo: `Yao Shunyu (姚顺雨)`.
PARENTHESIZED = re.compile(r"[(（][^()（）\n]*[)）]")
COMMENT = re.compile(r"(?<!\\)%.*$", re.M)


def body(text: str) -> str:
    begin = text.find("\\begin{document}")
    return text[begin:] if begin >= 0 else text


def counts(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def multiset(pattern: str, text: str) -> collections.Counter:
    return collections.Counter(re.findall(pattern, text))


def listing_line_counts(text: str) -> list[int]:
    return [len(b.strip("\n").splitlines())
            for b in re.findall(r"\\begin\{lstlisting\}(?:\[[^\]]*\])?(.*?)\\end\{lstlisting\}", text, re.S)]


def inputs(text: str) -> list[str]:
    return re.findall(r"\\(?:input|include)\{([^}]+)\}", text)


def keep_terms(glossary: Path) -> list[str]:
    if not glossary.is_file():
        return []
    with glossary.open(encoding="utf-8", newline="") as handle:
        return [r["term_en"].strip() for r in csv.DictReader(handle, delimiter="\t")
                if (r.get("decision") or "").strip() == "keep" and (r.get("term_en") or "").strip()]


def compare(zh_text: str, es_text: str, glossary: Path) -> list[tuple[str, str]]:
    zh_src, es_src = COMMENT.sub("", zh_text), COMMENT.sub("", es_text)
    zh, es = body(zh_src), body(es_src)
    out: list[tuple[str, str]] = []

    def same_count(key: str, pattern: str) -> None:
        a, b = counts(pattern, zh), counts(pattern, es)
        if a != b:
            out.append((f"parity:{key}", f"zh={a} es={b}"))

    same_count("sections", r"\\section\*?\{")
    same_count("subsections", r"\\subsection\*?\{")
    same_count("subsubsections", r"\\subsubsection\*?\{")
    for box in sorted(set(re.findall(r"\\begin\{(\w*box)\}", zh + es))):
        same_count(f"boxes:{box}", rf"\\begin\{{{box}\}}")
    same_count("figures", r"\\begin\{figure\*?\}|\\(?:videofigure|lecturefigure)\{")
    same_count("formulas", r"\\\[|\$\$|\\begin\{(?:equation|align|gather|multline)\*?\}")
    same_count("tables", r"\\begin\{(?:tabular|tabularx|longtable)\}")
    same_count("footnotes", r"\\footnote(?:text)?\{")

    for key, pattern in [
        ("images", r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"),
        ("labels", r"\\label\{([^}]+)\}"),
        ("refs", r"\\(?:ref|eqref|autoref|pageref)\{([^}]+)\}"),
        ("urls", r"\\(?:href|url)\{([^}]+)\}"),
    ]:
        a, b = multiset(pattern, zh), multiset(pattern, es)
        if key == "images":
            # `x.es-mx.png` es la misma figura que `x.png`, con su texto traducido.
            b = type(b)(re.sub(r"\.es-mx(\.\w+)$", r"\1", k) for k in b.elements())
        if a != b:
            missing = sorted((a - b).elements())[:3]
            extra = sorted((b - a).elements())[:3]
            out.append((f"parity:{key}", f"faltan={missing} sobran={extra}"))

    if listing_line_counts(zh) != listing_line_counts(es):
        out.append(("parity:listings", f"lineas zh={listing_line_counts(zh)} es={listing_line_counts(es)}"))

    expected = [re.sub(r"\.tex$", "", p) + ".es-mx.tex" if not p.endswith(".es-mx.tex") else p for p in inputs(zh_src)]
    if inputs(es_src) != expected:
        out.append(("parity:inputs", f"esperado={expected} es={inputs(es_src)}"))

    if re.search(r"\\usepackage(?:\[[^\]]*\])?\{ctex\}", es_src):
        out.append(("parity:ctex", "la traduccion sigue cargando ctex"))

    # Todo el documento, preámbulo incluido: `\notetitle` se imprime en la portada.
    residual = [(n, line.strip()) for n, line in enumerate(es_src.splitlines(), 1)
                if HAN.search(PARENTHESIZED.sub("", line))]
    if residual:
        out.append(("parity:residual-han", f"{len(residual)} linea(s); primera: {residual[0][1][:80]}"))

    for term in keep_terms(glossary):
        # El plural inglés cuenta como el término: el chino no flexiona y la
        # traducción escribe, bien, «tokens» donde el original dice «token».
        pattern = re.compile(rf"(?<![A-Za-z]){re.escape(term)}s?(?![A-Za-z])", re.I)
        if pattern.search(zh) and not pattern.search(es):
            out.append((f"parity:keep-term:{term.lower()}", "esta en la nota zh y no en la es-MX"))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("zh", type=Path)
    parser.add_argument("es", type=Path)
    parser.add_argument("--glossary", type=Path, default=DEFAULT_GLOSSARY)
    args = parser.parse_args(argv)
    for path in (args.zh, args.es):
        if not path.is_file():
            print(f"check_translation_parity: no existe {path}", file=sys.stderr)
            return 2
    found = compare(args.zh.read_text(encoding="utf-8"), args.es.read_text(encoding="utf-8"), args.glossary)
    for key, detail in found:
        print(f"{key}\t{detail}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
