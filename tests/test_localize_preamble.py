"""Conversion automatica al es-MX de preambulos y plantillas.

Lo que depende del idioma en un preambulo es fijo y se repite: `ctex`, la
opcion `extendedchars` de listings y las etiquetas de la portada. Se convierte
con una tabla; el chino que la tabla no reconoce se reporta, no se adivina.
El cuerpo de una nota no se toca: es trabajo del traductor.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "localize_preamble.py"
HAN = re.compile(r"[\u4e00-\u9fff]")


def run(src: Path, dst: Path):
    return subprocess.run([sys.executable, str(SCRIPT), str(src), str(dst)], capture_output=True, text=True)


def test_cs336_2026_template_is_localized(tmp_path: Path) -> None:
    out = tmp_path / "cs336-2026-notes-template.es-mx.tex"
    result = run(REPO_ROOT / "tools/templates/cs336-2026-notes-template.tex", out)
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "ctex" not in text
    assert "\\setdefaultlanguage[variant=mexican]{spanish}" in text
    assert "extendedchars=true" in text and "extendedchars=false" not in text
    assert "\\textbf{Autor o canal del video}:" in text
    assert "\\textbf{Duración del video}:" in text
    assert not HAN.search(text), [l for l in text.splitlines() if HAN.search(l)]


def test_unknown_chinese_is_reported_not_guessed(tmp_path: Path) -> None:
    src = tmp_path / "p.tex"
    src.write_text("\\usepackage[fontset=fandol]{ctex}\n\\newcommand{\\noteauthors}{基于某位讲者的授课整理}\n"
                   "\\textbf{视频时长}：x\n", encoding="utf-8")
    result = run(src, tmp_path / "p.es-mx.tex")
    assert result.returncode == 3
    assert "基于某位讲者的授课整理" in result.stderr
    out = (tmp_path / "p.es-mx.tex").read_text(encoding="utf-8")
    assert "\\textbf{Duración del video}: x" in out
    assert "基于某位讲者的授课整理" in out, "lo no reconocido se deja intacto"


def test_note_body_is_left_to_the_translator(tmp_path: Path) -> None:
    src = tmp_path / "lecture01-notes.tex"
    src.write_text("\\documentclass{article}\n\\usepackage[fontset=fandol]{ctex}\n"
                   "\\begin{document}\n\\section{总结与延伸}\n课堂提示\n\\end{document}\n", encoding="utf-8")
    result = run(src, tmp_path / "lecture01-notes.es-mx.tex")
    out = (tmp_path / "lecture01-notes.es-mx.tex").read_text(encoding="utf-8")
    assert "polyglossia" in out
    assert "\\section{总结与延伸}\n课堂提示" in out
    assert result.returncode == 0, "el chino del cuerpo no se reporta: no es del preambulo"


def test_conversion_is_idempotent(tmp_path: Path) -> None:
    once = tmp_path / "once.tex"
    twice = tmp_path / "twice.tex"
    run(REPO_ROOT / "tools/templates/cs336-2026-notes-template.tex", once)
    run(once, twice)
    assert once.read_text(encoding="utf-8") == twice.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("xelatex") is None, reason="xelatex no esta")
def test_localized_template_compiles(tmp_path: Path) -> None:
    out = tmp_path / "t.tex"
    run(REPO_ROOT / "tools/templates/cs336-2026-notes-template.tex", out)
    text = out.read_text(encoding="utf-8")
    text = text.replace("%% --- Inicio del contenido --- %%",
                        "%% --- Inicio del contenido --- %%\n\\section{Tokenización}\nAño y pingüino.\n", 1)
    out.write_text(text, encoding="utf-8")
    # La plantilla apunta a cover.jpg por defecto; la prueba mide el idioma, no la portada.
    from PIL import Image
    Image.new("RGB", (64, 36), "gray").save(tmp_path / "cover.jpg")
    result = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", out.name],
                            cwd=tmp_path, capture_output=True, text=True, timeout=300)
    assert (tmp_path / "t.pdf").is_file(), result.stdout[-2000:]


def test_residual_lines_are_reported_once(tmp_path: Path) -> None:
    """Un archivo incluido no tiene `\\begin{document}`: su titlepage cae dentro del preambulo."""
    src = tmp_path / "notes-shared.tex"
    src.write_text("\\newcommand{\\x}{y}\n\\begin{titlepage}\n\\textbf{未知标签}：z\n\\end{titlepage}\n", encoding="utf-8")
    result = run(src, tmp_path / "out.tex")
    assert result.returncode == 3
    assert result.stderr.count("未知标签") == 1, result.stderr


def test_front_matter_punctuation_and_cs329a_labels(tmp_path: Path) -> None:
    out = tmp_path / "notes-shared.es-mx.tex"
    result = run(REPO_ROOT / "cs329a/notes-shared.tex", out)
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert not HAN.search(text), [l for l in text.splitlines() if HAN.search(l)]
    assert "\\textbf{Curso}: Stanford CS329A Self-Improving AI Agents (Autumn 2025)" in text
    assert not re.search(r"[（）：。，]", text), [l for l in text.splitlines() if re.search(r"[（）：。，]", l)]
