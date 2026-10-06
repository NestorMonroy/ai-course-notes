#!/usr/bin/env python3
"""Suite de cualificación de tarea del ciclo es-MX, en el formato de thyrox (TASK-THYROX-0780).

thyrox no sabe traducir notas: puntúa con comprobaciones deterministas los casos
que el consumidor le da (``local-models-qualify --suite``). Este guion los
escribe con el trabajo real del ciclo:

- cada caso es un fragmento chino de un lote ya traducido, con el mismo prompt
  que ``translate`` envía (``build_prompt``) y el fragmento dentro del mensaje;
- las comprobaciones salen del fragmento y de las listas del proyecto: los
  marcadores ``<<<ES``/``ES>>>``, cero chino, la estructura LaTeX y ninguna
  forma prohibida;
- sólo se exige lo que la traducción aceptada de ese fragmento cumple, para que
  una traducción correcta pueda aprobar.

La cualificación es de la clase ``analysis``, la que ``translate`` pide, y se
escribe en el archivo de cualificaciones de ESTE proyecto: aprueba el modelo para
este trabajo, no para el de otro consumidor.

Métrica: comprobaciones derivadas del fragmento, binarias.
Ciega a: la fidelidad del sentido, que ninguna comprobación léxica ve.

Uso:
    qualification_suite.py --chunks DIR [--count N] --out SUITE.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SUITE_ID = "es-mx-translation@1"
# La clase la declara el ciclo de traducción; la suite no tiene una propia.
from translation_loop import DEFAULT_TASK_CLASS as TASK_CLASS  # noqa: E402
BEGIN_MARK, END_MARK = "<<<ES", "ES>>>"
#: El mismo rango que ``translation_loop.HAN``: lo que el ciclo cuenta como chino residual.
HAN_PATTERN = "[\\u4e00-\\u9fff]"
HAN = re.compile(r"[\u4e00-\u9fff]")
COMMENT_LINE = re.compile(r"(?<!\\)%.*$", re.M)
STRUCTURE = re.compile(r"\\(?:label|ref|eqref|cite|begin|end)\{[^}]*\}")
GRAPHIC_PATH = re.compile(r"\\includegraphics(?:\[[^\]]*\])?(\{[^}]*\})")
#: Los sintácticos de una RegExp de JavaScript: con la bandera ``u`` sólo ésos se escapan.
REGEX_SYNTAX = set("\\^$.*+?()[]{}|/")
#: Un fragmento más largo no cabe, con el prompt, en el contexto que se cualifica.
MAX_FRAGMENT_CHARS = 3500
DEFAULT_CASE_COUNT = 6
FRAGMENT_INSTRUCTION = ("El fragmento ya está leído y va aquí abajo; no uses herramientas. "
                        "Responde con su traducción entre <<<ES y ES>>>.")


def structure_tokens(text: str) -> list[str]:
    """Los comandos de estructura y las rutas de figura del fragmento, sin los comentados, en orden."""
    visible = COMMENT_LINE.sub("", text)
    tokens = STRUCTURE.findall(visible) + GRAPHIC_PATH.findall(visible)
    return list(dict.fromkeys(tokens))


def forbidden_pattern(form: str) -> str:
    """La forma, literal, con su primera letra en las dos cajas: el inicio de oración la capitaliza."""
    escaped = "".join(f"\\{char}" if char in REGEX_SYNTAX else char for char in form)
    first = next((index for index, char in enumerate(escaped) if char.isalpha()), None)
    if first is None:
        return escaped
    letter = escaped[first]
    return f"{escaped[:first]}[{letter.upper()}{letter.lower()}]{escaped[first + 1:]}"


def reference_of(zh_path: Path) -> Path:
    return zh_path.with_name(zh_path.name.replace(".zh.tex", ".es.tex"))


def case_for(zh_path: Path, prompt: str, forbidden: list[tuple[str, str | None]]) -> dict:
    zh = zh_path.read_text(encoding="utf-8")
    reference = reference_of(zh_path).read_text(encoding="utf-8")
    checks = [{"kind": "includes", "text": BEGIN_MARK}, {"kind": "includes", "text": END_MARK}]
    if not HAN.search(reference):
        checks.append({"kind": "excludes-pattern", "pattern": HAN_PATTERN})
    checks += [{"kind": "includes", "text": token} for token in structure_tokens(zh) if token in reference]
    checks += [{"kind": "excludes-pattern", "pattern": forbidden_pattern(form)}
               for form, _substitute in forbidden if form not in reference.lower()]
    return {
        "id": f"{zh_path.parent.name}/{zh_path.name.split('.')[0]}",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Item: {zh_path}\n\n{FRAGMENT_INSTRUCTION}\n\n{zh}"},
        ],
        "checks": checks,
    }


def usable(zh_path: Path) -> bool:
    text = zh_path.read_text(encoding="utf-8")
    return reference_of(zh_path).is_file() and bool(HAN.search(text)) and len(text) <= MAX_FRAGMENT_CHARS


def select_fragments(chunks: Path, count: int) -> list[Path]:
    """``count`` fragmentos repartidos por tamaño, de menor a mayor; el mismo resultado cada vez."""
    candidates = sorted((path for path in chunks.rglob("*.zh.tex") if usable(path)),
                        key=lambda path: (len(path.read_text(encoding="utf-8")), str(path)))
    if len(candidates) <= count:
        return candidates
    step = (len(candidates) - 1) / (count - 1) if count > 1 else 0
    return [candidates[round(index * step)] for index in range(count)]


def build_suite(fragments: list[Path], prompt: str, forbidden: list[tuple[str, str | None]]) -> dict:
    return {"id": SUITE_ID, "taskClass": TASK_CLASS, "cases": [case_for(path, prompt, forbidden) for path in fragments]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", type=Path, required=True, help="el directorio chunks/ de un lote ya traducido")
    parser.add_argument("--count", type=int, default=DEFAULT_CASE_COUNT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    import check_prose_vocabulary as prose
    import translation_loop as loop
    fragments = select_fragments(args.chunks.resolve(), args.count)
    if not fragments:
        print(f"qualification_suite: ningún fragmento usable en {args.chunks}", file=sys.stderr)
        return 2
    built = build_suite(fragments, loop.build_prompt(loop.DEFAULT_MEMORY), prose.load_forbidden(prose.DEFAULT_FORBIDDEN))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(built, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"qualification_suite: {len(fragments)} caso(s) → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
