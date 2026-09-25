"""Comentarios, docstrings y mensajes en español con sus tildes y eñes.

Los identificadores van en inglés; los comentarios en español, y el español sin
tildes ni eñe (`traduccion`, `espanol`, `senal`) es un defecto, no una variante.
`check_comment_spelling.py` aplica a esos tramos el eje `unaccented` de la
prosa, con el mismo diccionario es_MX, y `--fix` corrige solo dentro de ellos.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "check_comment_spelling.py"

PY = '''"""La traduccion al espanol de la senal."""
# Una funcion que calcula la senal.
def senal_value(traduccion):
    return "codigo"  # el codigo
'''


def run(*args: str):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO_ROOT)


def test_comments_and_docstrings_are_checked_but_code_is_not(tmp_path: Path) -> None:
    src = tmp_path / "module.py"
    src.write_text(PY, encoding="utf-8")
    result = run(str(src))
    assert result.returncode == 1
    assert "module.py:1: traduccion → traducción" in result.stdout
    assert "module.py:2: funcion → función" in result.stdout
    assert "module.py:4: codigo → código" in result.stdout
    # El identificador `senal_value` y el parámetro `traduccion` son código;
    # la cadena "codigo" de la línea 4 no es un comentario.
    assert result.stdout.count("module.py:3:") == 0
    assert result.stdout.count("module.py:4:") == 1


def test_fix_rewrites_only_the_comment_spans(tmp_path: Path) -> None:
    src = tmp_path / "module.py"
    src.write_text(PY, encoding="utf-8")
    assert run("--fix", str(src)).returncode == 0
    fixed = src.read_text(encoding="utf-8")
    assert '"""La traducción al español de la señal."""' in fixed
    assert "# Una función que calcula la señal." in fixed
    assert "def senal_value(traduccion):" in fixed
    assert 'return "codigo"  # el código' in fixed
    assert run(str(src)).returncode == 0


def test_shell_comments_and_markdown_prose(tmp_path: Path) -> None:
    sh = tmp_path / "tool.sh"
    # La línea 3 lleva un `#` dentro de comillas: es texto de `echo`, no comentario.
    sh.write_text('#!/bin/bash\n# instalacion opt-in\necho "paso #1: instalacion"\n', encoding="utf-8")
    md = tmp_path / "NOTES.md"
    md.write_text("# Guia\n\nLa traduccion va aqui.\n\n```bash\necho traduccion\n```\n", encoding="utf-8")
    result = run(str(sh), str(md))
    assert "tool.sh:2: instalacion → instalación" in result.stdout
    assert "tool.sh:3:" not in result.stdout
    assert "NOTES.md:3: traduccion → traducción" in result.stdout
    assert "NOTES.md:6:" not in result.stdout  # bloque de código
