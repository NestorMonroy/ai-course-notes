"""Paridad estructural entre la nota zh y su traducción es-MX (V1-V3 del plan).

Traducir no puede perder ni inventar estructura: secciones, cajas, figuras,
formulas, listings, tablas, etiquetas, referencias, enlaces. Tampoco puede
dejar chino fuera de los originales entre paréntesis, ni traducir un término
que el glosario manda dejar en inglés.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "check_translation_parity.py"

ZH = r"""\documentclass{article}
\usepackage[fontset=fandol]{ctex}
\input{../cs25-preamble.tex}
\begin{document}
\section{分词}\label{sec:tok}
见 \ref{fig:a}，详见 \href{https://example.com}{官网}。每个 token 都有 embedding。
\begin{knowledgebox}{读图：损失曲线}
曲线。
\end{knowledgebox}
\begin{figure}\includegraphics{images/a.png}\label{fig:a}\end{figure}
\[ x = y \]
\begin{lstlisting}
x = 1  # 注释
y = 2
\end{lstlisting}
\begin{tabular}{cc} a & b \end{tabular}
\subsection{本章小结}
小结。
\end{document}
"""

ES = r"""\documentclass{article}
\usepackage{polyglossia}
\input{../cs25-preamble.es-mx.tex}
\begin{document}
\section{Tokenización}\label{sec:tok}
Ver \ref{fig:a}; detalles en \href{https://example.com}{el sitio}. Cada token tiene su embedding. Yao Shunyu (姚顺雨).
\begin{knowledgebox}{Lectura de la figura: la curva de pérdida}
La curva.
\end{knowledgebox}
\begin{figure}\includegraphics{images/a.png}\label{fig:a}\end{figure}
\[ x = y \]
\begin{lstlisting}
x = 1  # comentario
y = 2
\end{lstlisting}
\begin{tabular}{cc} a & b \end{tabular}
\subsection{Resumen de la sección}
Resumen.
\end{document}
"""


def check(tmp_path: Path, es_text: str, zh_text: str = ZH):
    zh = tmp_path / "lecture01-notes.tex"
    es = tmp_path / "lecture01-notes.es-mx.tex"
    zh.write_text(zh_text, encoding="utf-8")
    es.write_text(es_text, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(zh), str(es)], capture_output=True, text=True)


def signals(result) -> set[str]:
    return {line.split("\t")[0] for line in result.stdout.splitlines() if line.startswith("parity:")}


def test_faithful_translation_has_no_signals(tmp_path: Path) -> None:
    result = check(tmp_path, ES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert signals(result) == set()


def test_lost_structure_is_reported(tmp_path: Path) -> None:
    es = (ES.replace("\\begin{knowledgebox}{Lectura de la figura: la curva de pérdida}\nLa curva.\n\\end{knowledgebox}\n", "")
            .replace("\\[ x = y \\]\n", "")
            .replace("\\subsection{Resumen de la sección}\n", ""))
    got = signals(check(tmp_path, es))
    assert {"parity:boxes:knowledgebox", "parity:formulas", "parity:subsections"} <= got


def test_changed_references_images_urls_and_inputs_are_reported(tmp_path: Path) -> None:
    es = (ES.replace("images/a.png", "images/b.png").replace("\\ref{fig:a}", "\\ref{fig:b}")
            .replace("https://example.com", "https://otro.example.com")
            .replace("cs25-preamble.es-mx.tex", "cs25-preamble.tex"))
    got = signals(check(tmp_path, es))
    assert {"parity:images", "parity:refs", "parity:urls", "parity:inputs"} <= got


def test_listing_line_count_must_match(tmp_path: Path) -> None:
    es = ES.replace("x = 1  # comentario\ny = 2\n", "x = 1  # comentario\n")
    assert "parity:listings" in signals(check(tmp_path, es))


def test_residual_chinese_outside_parentheses_is_reported(tmp_path: Path) -> None:
    es = ES.replace("Resumen.", "Resumen. 本章小结")
    result = check(tmp_path, es)
    assert "parity:residual-han" in signals(result)
    assert "姚顺雨" not in result.stdout, "el original entre parentesis esta permitido"


def test_keep_term_translated_away_is_reported(tmp_path: Path) -> None:
    es = ES.replace("Cada token tiene su embedding.", "Cada ficha tiene su incrustación.")
    got = signals(check(tmp_path, es))
    assert "parity:keep-term:token" in got and "parity:keep-term:embedding" in got


def test_the_english_plural_of_a_kept_term_counts_as_the_term(tmp_path: Path) -> None:
    # El chino no flexiona: el original dice «token» y la traducción, bien,
    # «Cada uno de los tokens». No es un término traducido fuera.
    es = ES.replace("Cada token tiene su embedding.", "Todos los tokens tienen sus embeddings.")
    got = signals(check(tmp_path, es))
    assert "parity:keep-term:token" not in got and "parity:keep-term:embedding" not in got, got


def test_ctex_left_in_the_translation_is_reported(tmp_path: Path) -> None:
    es = ES.replace("\\usepackage{polyglossia}", "\\usepackage[fontset=fandol]{ctex}")
    assert "parity:ctex" in signals(check(tmp_path, es))


def test_chinese_left_in_the_preamble_is_residual(tmp_path: Path) -> None:
    # `\notetitle` vive en el preámbulo y se imprime en la portada; la fuente
    # latina no tiene esos glifos y XeLaTeX los omite en silencio.
    title_zh = ZH.replace("\\begin{document}", "\\newcommand{\\notetitle}{自我改进}\n\\begin{document}", 1)
    left = ES.replace("\\begin{document}", "\\newcommand{\\notetitle}{自我改进}\n\\begin{document}", 1)
    assert "parity:residual-han" in signals(check(tmp_path, left, title_zh))
    done = left.replace("自我改进", "Automejora")
    assert "parity:residual-han" not in signals(check(tmp_path, done, title_zh))
