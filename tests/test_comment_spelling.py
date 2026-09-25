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
    # la cadena `"codigo"` de la línea 4 no es un comentario.
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


def test_prohibited_forms_in_comments_are_reported(tmp_path: Path) -> None:
    # «corrida» está en `prohibited_forms.txt` (→ ejecución) y se escribió 11
    # veces en comentarios y bancos: el gate de prosa solo mira las notas.
    src = tmp_path / "module.py"
    src.write_text('"""Mide la primera corrida."""\n# Cada corrida escribe su carpeta.\n'
                   'RUNS = "corrida"  # cadena de código, no comentario\n', encoding="utf-8")
    md = tmp_path / "README.md"
    md.write_text("| primera corrida | resultado |\n\n```\ncorrida\n```\n", encoding="utf-8")
    result = run(str(src), str(md))
    assert result.returncode == 1
    assert "module.py:1: corrida (prohibida)" in result.stdout
    assert "module.py:2: corrida (prohibida)" in result.stdout
    assert "README.md:1: corrida (prohibida)" in result.stdout
    assert "module.py:3:" not in result.stdout and "README.md:4:" not in result.stdout


def test_a_quoted_form_is_a_citation_not_a_use(tmp_path: Path) -> None:
    # La plantilla del traductor y el glosario citan las formas prohibidas para
    # prohibirlas: entre `…` o «…» es una cita; sin comillas, un uso.
    src = tmp_path / "rules.py"
    src.write_text("# No escribas «corrida» ni `chamba`; tampoco la traduccion `espanol`.\n"
                   "# La corrida de hoy.\n", encoding="utf-8")
    result = run(str(src))
    assert "rules.py:1: corrida" not in result.stdout and "rules.py:1: chamba" not in result.stdout
    assert "rules.py:1: espanol" not in result.stdout
    assert "rules.py:1: traduccion → traducción" in result.stdout
    assert "rules.py:2: corrida (prohibida)" in result.stdout


def test_only_spanish_spans_are_judged_and_proper_names_are_kept(tmp_path: Path) -> None:
    # Medido en el barrido de la rama: `AGENTS.md` está en inglés y el gate le
    # proponía `names → ñames`, `multiple → múltiple`, `version → versión`.
    src = tmp_path / "mixed.py"
    src.write_text("# Keep the names and continue with multiple versions via the table.\n"
                   "# Se construye desde el paquete de Debian con LaTeX, y la traduccion.\n"
                   "# Traduccion de la seccion.\n", encoding="utf-8")
    result = run(str(src))
    assert "mixed.py:1:" not in result.stdout, result.stdout
    assert "mixed.py:2: Debian" not in result.stdout and "LaTeX" not in result.stdout
    assert "mixed.py:2: traduccion → traducción" in result.stdout
    # Al inicio de oración la mayúscula no es un nombre propio.
    assert "mixed.py:3: Traduccion → Traducción" in result.stdout


def test_english_lines_and_documents_measured_in_the_branch_are_not_judged(tmp_path: Path) -> None:
    # Casos reales del barrido: un comentario inglés del archivo original y una
    # fila de tabla de `AGENTS.md`, que está en inglés.
    src = tmp_path / "coverage.py"
    src.write_text("# narrative prose. Count them elsewhere via boxes/term digestion.\n"
                   "# La version del traductor usa THYROX via headless-pool.\n", encoding="utf-8")
    guide = tmp_path / "GUIDE.md"
    guide.write_text("# Agent Guide\n\nThe notes are compiled with XeLaTeX and the site is built from them.\n"
                     "Use the scripts in this repository when you generate a note.\n\n"
                     "| Directory | What goes there |\n|---|---|\n| `.claude/jobs/` | background job records |\n",
                     encoding="utf-8")
    result = run(str(src), str(guide))
    assert "coverage.py:1:" not in result.stdout, result.stdout
    assert "coverage.py:2: version → versión" in result.stdout
    assert "coverage.py:2: via → vía" in result.stdout
    assert "GUIDE.md" not in result.stdout
