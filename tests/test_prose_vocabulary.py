"""Vocabulario de la prosa es-MX: los cuatro ejes del gate de idioma.

Adaptado del gate de THYROX (`check_vocabulario_prosa.py`, palabra inventada y
forma prohibida) y ampliado con dos ejes que el pedido exige: spanglish (raiz
inglesa con terminacion espanola) e ingles no declarado en el glosario.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "check_prose_vocabulary.py"

PREAMBLE = "\\documentclass{article}\n\\usepackage{polyglossia}\n\\begin{document}\n"
END = "\n\\end{document}\n"


def note(tmp_path: Path, body: str, name: str = "lecture01-notes.es-mx.tex") -> Path:
    path = tmp_path / name
    path.write_text(PREAMBLE + body + END, encoding="utf-8")
    return path


def run(*args: str, cwd: Path | None = None, python: str = sys.executable, glossary: Path | None = None):
    cmd = [python, str(SCRIPT), "--no-baseline", *args]
    if glossary is not None:
        cmd += ["--glossary", str(glossary)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT)


def test_invented_word_is_reported(tmp_path: Path) -> None:
    result = run(str(note(tmp_path, "La democión del modelo.")))
    assert result.returncode == 1, result.stderr
    assert "democión" in result.stdout


def test_prohibited_form_is_reported_with_its_file(tmp_path: Path) -> None:
    result = run(str(note(tmp_path, "Esa es la regla de oro del entrenamiento.")))
    assert result.returncode == 1
    assert "lecture01-notes.es-mx.tex::regla de oro" in result.stdout


def test_spanglish_is_reported_and_spanish_is_not(tmp_path: Path) -> None:
    body = ("Hay que deployear el modelo y commitear el cambio antes de testear. "
            "Conviene plantear, organizar y formatear los datos.")
    result = run(str(note(tmp_path, body)))
    for word in ("deployear", "commitear", "testear"):
        assert f"spanglish:{word}" in result.stdout, result.stdout
    for word in ("plantear", "organizar", "formatear"):
        assert f"spanglish:{word}" not in result.stdout


def test_undeclared_english_is_reported_unless_in_glossary(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary.tsv"
    glossary.write_text(
        "term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
        "pipeline\tkeep\t\tsecuencia de etapas\t\t\n",
        encoding="utf-8",
    )
    body = ("El pipeline ajusta los weights del modelo. Stanford publicó el curso. Año y niño. "
            "El artículo Attention Is All You Need introdujo el Transformer.")
    result = run(str(note(tmp_path, body)), glossary=glossary)
    assert "english:weights" in result.stdout, result.stdout
    assert "english:pipeline" not in result.stdout
    assert "english:stanford" not in result.stdout
    # Un titulo o nombre propio en ingles va con mayuscula y no es prosa a traducir.
    assert "english:attention" not in result.stdout
    assert "english:año" not in result.stdout


def test_glossary_rejected_forms_are_prohibited(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary.tsv"
    glossary.write_text(
        "term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
        "embedding\tkeep\t\trepresentación vectorial\t\timbibición|incrustación\n",
        encoding="utf-8",
    )
    result = run(str(note(tmp_path, "La imbibición de cada token.")), glossary=glossary)
    assert result.returncode == 1
    assert "::imbibición" in result.stdout


def test_latex_code_urls_math_and_commands_are_not_prose(tmp_path: Path) -> None:
    body = (
        "Texto normal.\n"
        "\\texttt{deployear} y \\verb|commitear| y \\url{https://example.com/weights}\n"
        "% comentario con la regla de oro y weights\n"
        "$weights = x$\n"
        "\\begin{lstlisting}\ndeployear()  # weights\n\\end{lstlisting}\n"
        "\\includegraphics{images/weights.png}\n"
    )
    result = run(str(note(tmp_path, body)))
    assert result.returncode == 0, result.stdout
    assert "0 hallazgo" in result.stdout


def test_preamble_is_not_prose(tmp_path: Path) -> None:
    path = tmp_path / "lecture01-notes.es-mx.tex"
    path.write_text(
        "\\documentclass{article}\n% la regla de oro en el preambulo\n"
        "\\newcommand{\\notetitle}{weights}\n\\begin{document}\nTexto.\n\\end{document}\n",
        encoding="utf-8",
    )
    result = run(str(path))
    assert result.returncode == 0, result.stdout


def test_baseline_freezes_a_listed_finding(tmp_path: Path) -> None:
    path = note(tmp_path, "La democión del modelo.")
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("# congelado\ndemoción\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--baseline", str(baseline), str(path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout
    assert "1 en baseline" in result.stdout


def test_scope_is_the_changed_spanish_notes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", "-b", "es-mx"], cwd=repo, check=True)
    (repo / "old-notes.es-mx.tex").write_text(PREAMBLE + "La democión." + END, encoding="utf-8")
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-qb", "feature/x"], cwd=repo, check=True)

    empty = run("--base", "es-mx", cwd=repo)
    assert empty.returncode == 0, empty.stdout + empty.stderr
    assert "0 archivo(s)" in empty.stdout

    (repo / "new-notes.es-mx.tex").write_text(PREAMBLE + "Una chamba." + END, encoding="utf-8")
    (repo / "new-notes.tex").write_text(PREAMBLE + "chamba" + END, encoding="utf-8")
    scoped = run("--base", "es-mx", cwd=repo)
    assert scoped.returncode == 1
    assert "new-notes.es-mx.tex::chamba" in scoped.stdout
    assert "new-notes.tex::" not in scoped.stdout
    assert "democión" not in scoped.stdout


def test_missing_lexicon_refuses_without_a_count(tmp_path: Path) -> None:
    """Sin el lexico no se emite cifra: un cero no distinguiria «limpio» de «no medi»."""
    result = run(str(note(tmp_path, "Texto.")), python="/usr/bin/python3")
    assert result.returncode == 2
    assert "uv sync" in result.stderr
    assert "hallazgo" not in result.stdout


def test_spanish_verb_forms_known_to_the_lemma_table_are_not_spanglish(tmp_path: Path) -> None:
    """La conjugacion rara de un verbo espanol no es spanglish si spaCy le conoce lema.

    Medido: `horneado`, `formateado` y `sorteado` son formas de hornear, formatear
    y sortear, y el eje las marcaba porque la forma conjugada es rara en el
    corpus y su raiz (`horn`, `format`, `sort`) es inglesa. La tabla de lemas de
    spacy-lookups-data las conoce; a `testeado` o `pusheado` no.
    """
    body = "El pan horneado, el texto formateado y el premio sorteado. Lo testeado y lo pusheado."
    result = run(str(note(tmp_path, body)))
    for word in ("horneado", "formateado", "sorteado"):
        assert f"spanglish:{word}" not in result.stdout, result.stdout
    for word in ("testeado", "pusheado"):
        assert f"spanglish:{word}" in result.stdout, result.stdout


def test_glossary_translated_form_is_not_invented(tmp_path: Path) -> None:
    body = "La tokenización divide el texto."
    bare = tmp_path / "bare.tsv"
    bare.write_text("term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n", encoding="utf-8")
    assert "tokenización" in run(str(note(tmp_path, body)), glossary=bare).stdout
    declared = tmp_path / "declared.tsv"
    declared.write_text(
        "term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
        "tokenization\ttranslate\ttokenización\tdivisión del texto en tokens\tIATE:3592517\t\n",
        encoding="utf-8",
    )
    result = run(str(note(tmp_path, body)), glossary=declared)
    assert "tokenización" not in result.stdout, result.stdout
