#!/usr/bin/env python3
"""Convierte al es-MX el preambulo de una nota, un preambulo compartido o una
plantilla.

    localize_preamble.py <entrada.tex> <salida.es-mx.tex>

Lo que depende del idioma en un preambulo es fijo y se repite en los cuatro
preambulos compartidos y en las plantillas: `ctex`, `extendedchars=false` de
listings, el nombre «Listing» y las etiquetas de la portada. Se convierte con
una tabla; el cuerpo de una nota no se toca, porque su prosa es trabajo del
traductor.

Salida: 0 si no queda chino en el preambulo ni en la portada (`titlepage`);
3 si queda, con cada linea en stderr: la tabla no lo reconoce y no se adivina.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HAN = re.compile(r"[\u4e00-\u9fff]")

CTEX = re.compile(r"^\\usepackage(?:\[[^\]]*\])?\{ctex\}[^\n]*$", re.M)
SPANISH = (
    "% Espanol (Mexico) con XeLaTeX: fontspec para fuentes Unicode, polyglossia\n"
    "% para la division silabica y los nombres del documento en la variante mexicana.\n"
    "\\usepackage{fontspec}\n"
    "\\usepackage{polyglossia}\n"
    "\\setdefaultlanguage[variant=mexican]{spanish}\n"
    "% polyglossia no traduce los nombres de listings.\n"
    "\\AtBeginDocument{\\providecommand{\\lstlistingname}{}\\renewcommand{\\lstlistingname}{Listado}%\n"
    "  \\providecommand{\\lstlistlistingname}{}\\renewcommand{\\lstlistlistingname}{Índice de listados}}"
)

# Sustituciones exactas: etiquetas y marcadores que se repiten tal cual. El
# orden importa: las mas largas primero.
EXACT = [
    ("\\textbf{视频作者/频道}：", "\\textbf{Autor o canal del video}: "),
    ("\\textbf{发布日期}：", "\\textbf{Fecha de publicación}: "),
    ("\\textbf{视频时长}：", "\\textbf{Duración del video}: "),
    ("\\textbf{课程官网}：", "\\textbf{Sitio del curso}: "),
    ("\\textbf{视频链接}：", "\\textbf{Enlace del video}: "),
    ("\\textbf{项目主页}：", "\\textbf{Página del proyecto}: "),
    ("\\textbf{制作规范}：", "\\textbf{Normas de elaboración}: "),
    ("\\textbf{课程}：", "\\textbf{Curso}: "),
    ("\\textbf{本讲日期}：", "\\textbf{Fecha de la clase}: "),
    ("\\textbf{公开视频发布日期}：", "\\textbf{Fecha de publicación del video}: "),
    ("\\textbf{讲义制作日期}：", "\\textbf{Fecha de elaboración de las notas}: "),
    ("\\textbf{频道 / 时长}：", "\\textbf{Canal / duración}: "),
    ("）与本项目质量规范", ") y las normas de calidad de este proyecto"),
    ("\\footnotetext{视频讲解区间：#4。}", "\\footnotetext{Intervalo del video: #4.}"),
    ("\\begin{knowledgebox}{课堂提示}", "\\begin{knowledgebox}{Nota de clase}"),
    ("\\emph{来源：#1}", "\\emph{Fuente: #1}"),
    ("{\\Large 课程笔记\\par}", "{\\Large Notas del curso\\par}"),
    ("{\\small 请在生成笔记时填入视频封面图的本地路径。\\par}",
     "{\\small Al generar las notas, indique la ruta local de la portada del video.\\par}"),
    ("课程笔记：[在此填写课程主题]", "Notas del curso: [Escriba aquí el tema del curso]"),
    ("课程笔记：[课程主题]", "Notas del curso: [tema del curso]"),
    ("基于公开课程资料整理", "Elaboradas a partir de materiales públicos del curso"),
    ("[在此填写日期]", "[Escriba aquí la fecha]"),
    ("[在此填写频道或作者]", "[Escriba aquí el canal o el autor]"),
    ("[在此填写发布日期]", "[Escriba aquí la fecha de publicación]"),
    ("[在此填写视频时长]", "[Escriba aquí la duración del video]"),
    ("[发布日期]", "[fecha de publicación]"),
    ("[视频时长]", "[duración del video]"),
    ("%% --- 正文内容开始 --- %%", "%% --- Inicio del contenido --- %%"),
    ("%% --- 正文内容结束 --- %%", "%% --- Fin del contenido --- %%"),
]

# Sustituciones con patron: las que llevan un nombre de curso o un anio.
PATTERNS = [
    (re.compile(r"基于\s*(.+?)\s*公开课程资料整理"), r"Elaboradas a partir de los materiales públicos de \1"),
    (re.compile(r"基于\s*(.+?)\s*授课内容整理"), r"Elaboradas a partir de la clase de \1"),
    (re.compile(r"(\d{4})\s*年春季"), r"Primavera de \1"),
    (re.compile(r"(\d{4})\s*年秋季"), r"Otoño de \1"),
    (re.compile(r"(\d{4})\s*年重写版"), r"Versión reescrita en \1"),
    (re.compile(r"本仓库\s*(.+?)\s*标准"), r"las normas \1 de este repositorio"),
]

PUNCTUATION = [
    (re.compile(r"\s*（"), " ("),
    (re.compile(r"）"), ")"),
    (re.compile(r"：\s*"), ": "),
    (re.compile(r"。"), "."),
    (re.compile(r"，\s*"), ", "),
]


def front_matter_spans(text: str) -> list[tuple[int, int]]:
    """El preambulo (antes de `\\begin{document}`) y cada `titlepage`."""
    begin = text.find("\\begin{document}")
    spans = [(0, begin if begin >= 0 else len(text))]
    spans += [m.span() for m in re.finditer(r"\\begin\{titlepage\}.*?\\end\{titlepage\}", text, re.S)]
    # Un archivo incluido no tiene `\\begin{document}`: su preambulo es todo el
    # archivo y contiene a su titlepage. Los tramos se funden para no contar
    # dos veces la misma linea.
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


UNBRACED_TITLE = re.compile(r"title=(#\d)")


def localize(text: str) -> str:
    text = CTEX.sub(lambda _m: SPANISH, text)
    text = text.replace("extendedchars=false", "extendedchars=true")
    # `title=#1` sin llaves: en chino la coma del titulo es `，` y no separa
    # claves; en espanol una `,` parte la clave de pgfkeys en dos.
    text = UNBRACED_TITLE.sub(r"title={\1}", text)
    for old, new in EXACT:
        text = text.replace(old, new)
    # Los patrones solo se aplican donde viven los metadatos, nunca a la prosa.
    out, last = [], 0
    for start, end in front_matter_spans(text):
        out.append(text[last:start])
        chunk = text[start:end]
        for pattern, repl in PATTERNS:
            chunk = pattern.sub(repl, chunk)
        # La puntuacion de ancho completo de los metadatos, a la del espanol.
        for pattern, repl in PUNCTUATION:
            chunk = pattern.sub(repl, chunk)
        out.append(chunk)
        last = end
    out.append(text[last:])
    return "".join(out)


def residual(text: str) -> list[tuple[int, str]]:
    lines = []
    for start, end in front_matter_spans(text):
        first = text.count("\n", 0, start) + 1
        for offset, line in enumerate(text[start:end].splitlines()):
            if HAN.search(line):
                lines.append((first + offset, line.strip()))
    return lines


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = Path(argv[0]), Path(argv[1])
    text = localize(src.read_text(encoding="utf-8"))
    dst.write_text(text, encoding="utf-8")
    left = residual(text)
    for number, line in left:
        print(f"localize_preamble: {dst}:{number}: chino sin convertir: {line}", file=sys.stderr)
    return 3 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
