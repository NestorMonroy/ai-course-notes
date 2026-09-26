"""Vocabulario de la prosa es-MX: los cuatro ejes del gate de idioma.

Adaptado del gate de THYROX (`check_vocabulario_prosa.py`, palabra inventada y
forma prohibida) y ampliado con dos ejes que el pedido exige: spanglish (raíz
inglesa con terminación española) e inglés no declarado en el glosario.
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
    # Un titulo o nombre propio en inglés va con mayúscula y no es prosa a traducir.
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
    """Sin el léxico no se emite cifra: un cero no distinguiría «limpio» de «no medi»."""
    result = run(str(note(tmp_path, "Texto.")), python="/usr/bin/python3")
    assert result.returncode == 2
    assert "uv sync" in result.stderr
    assert "hallazgo" not in result.stdout


def test_spanish_verb_forms_known_to_the_lemma_table_are_not_spanglish(tmp_path: Path) -> None:
    """La conjugación rara de un verbo español no es spanglish si spaCy le conoce lema.

    Medido: `horneado`, `formateado` y `sorteado` son formas de hornear, formatear
    y sortear, y el eje las marcaba porque la forma conjugada es rara en el
    corpus y su raíz (`horn`, `format`, `sort`) es inglesa. La tabla de lemas de
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


def test_the_english_plural_of_a_kept_term_is_not_reported(tmp_path: Path) -> None:
    glossary = tmp_path / "glossary.tsv"
    glossary.write_text("term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
                        "prompt\tkeep\t\ttexto de entrada\t\t\n", encoding="utf-8")
    result = run(str(note(tmp_path, "Se comparan varios prompts y sus weights.")), glossary=glossary)
    assert "english:prompts" not in result.stdout, result.stdout
    assert "english:weights" in result.stdout


def test_spanish_verb_forms_that_look_english_are_not_english(tmp_path: Path) -> None:
    body = ("Que el modelo critique, revise y compare; que complete, explore y añada el diseño "
            "del año. Mide los outputs.")
    result = run(str(note(tmp_path, body)))
    for word in ("compare", "complete", "explore", "añada", "diseño", "año"):
        assert f"english:{word}" not in result.stdout and f"spanglish:{word}" not in result.stdout, result.stdout
    # `outputs` es inglés aunque la tabla de lemas lo lleve a `output`: el
    # diccionario es_MX no lo acepta.
    assert "english:outputs" in result.stdout


def test_a_spanish_infinitive_is_not_spanglish(tmp_path: Path) -> None:
    body = "Conviene externalizar la señal; no hay que deployear ni testear el código."
    result = run(str(note(tmp_path, body)))
    assert "spanglish:externalizar" not in result.stdout, result.stdout
    assert "spanglish:deployear" in result.stdout and "spanglish:testear" in result.stdout


def test_a_prefix_on_an_attested_word_is_not_invented(tmp_path: Path) -> None:
    body = ("La autoverificación, el posentrenamiento, las subexpresiones y la retropropagación "
            "de la señal; la democión no.")
    result = run(str(note(tmp_path, body)))
    for word in ("autoverificación", "posentrenamiento", "subexpresiones", "retropropagación"):
        assert word not in result.stdout, result.stdout
    assert "democión" in result.stdout


def test_spanish_written_without_accents_or_enie_is_reported(tmp_path: Path) -> None:
    # La prosa es-MX sin tildes ni eñe es un defecto, no una variante: el
    # diccionario es_MX rechaza «traduccion» y «espanol» y acepta sus formas.
    body = "La traduccion al espanol de la senal. La traducción al español de la señal."
    result = run(str(note(tmp_path, body)))
    for word in ("traduccion", "espanol", "senal"):
        assert f"unaccented:{word}" in result.stdout, result.stdout
    for word in ("traducción", "español", "señal"):
        assert f"unaccented:{word}" not in result.stdout
    # El léxico trae basura con tildes o símbolos (`reading→`, `model` con un
    # carácter roto): una palabra inglesa o una letra suelta no es «sin tildes».
    other = run(str(note(tmp_path, "El reading del model of h y p con la canción.", "otra.es-mx.tex")))
    for word in ("reading", "model", "of", "h", "p"):
        assert f"unaccented:{word}" not in other.stdout, other.stdout


def test_a_prefix_doubles_the_r_of_its_base(tmp_path: Path) -> None:
    # Ortografía: tras un prefijo que acaba en vocal, la r inicial se duplica
    # (auto + revisión → autorrevisión). cs329a, iteración 03.
    result = run(str(note(tmp_path, "La autorrevisión y la contrarréplica de la señal.")))
    assert "autorrevisión" not in result.stdout and "contrarréplica" not in result.stdout, result.stdout


def test_the_english_es_plural_counts_as_its_singular() -> None:
    # cs329a/lecture06: el original escribe «无效 batch» y la traducción, bien,
    # «batches»; `singular` quitaba solo la s y comparaba «batche».
    import importlib.util
    spec = importlib.util.spec_from_file_location("cpv", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # «batches» → batch pero «caches» → cache: el sufijo no decide, así que se
    # dan los dos candidatos y compara quien tiene el original o el glosario.
    for plural, single in [("batches", "batch"), ("boxes", "box"), ("prompts", "prompt"),
                           ("classes", "class"), ("caches", "cache")]:
        assert single in mod.singulars(plural), (plural, mod.singulars(plural))
    assert mod.singulars("class") == set()


def test_a_form_adopted_by_the_glossary_is_not_spanglish(tmp_path: Path) -> None:
    # Ola 1: `tokenizada` siguió saliendo como spanglish aunque el glosario
    # adoptó las formas de tokenizar; el eje spanglish no consultaba el glosario.
    glossary = tmp_path / "glossary.tsv"
    glossary.write_text("term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
                        "tokenize\ttranslate\ttokenizar tokenizada\tdividir en tokens\tIATE\t\n", encoding="utf-8")
    result = run(str(note(tmp_path, "La señal tokenizada y el código deployeado.")), glossary=glossary)
    assert "spanglish:tokenizada" not in result.stdout, result.stdout
    assert "spanglish:deployeado" in result.stdout


def test_package_and_language_names_are_preamble_code_not_prose(tmp_path: Path) -> None:
    # Un preámbulo compartido no tiene `\begin{document}` y se lee entero:
    # `\setdefaultlanguage[variant=mexican]{spanish}` salía como inglés en los
    # cinco preámbulos es-MX (medición del 2026-09-25). El nombre de un paquete,
    # una clase o un idioma, con su opción, es código; un `\caption[…]` es prosa.
    preamble = tmp_path / "curso-preamble.es-mx.tex"
    preamble.write_text("% Español de México, con su división silábica.\n"
                        "\\setdefaultlanguage[variant=mexican]{spanish}\n"
                        "\\usepackage[margin=2cm,headheight=14pt]{geometry}\n"
                        "\\caption[El deployment del año]{Figura}\n", encoding="utf-8")
    result = run(str(preamble))
    assert "english:variant" not in result.stdout, result.stdout
    assert "english:mexican" not in result.stdout and "english:margin" not in result.stdout
    assert "english:geometry" not in result.stdout
    assert "deployment" in result.stdout


def test_the_unaccented_axis_skips_proper_names_and_units_after_a_number(tmp_path: Path) -> None:
    # Ola 4: «Microsoft Research Asia», «Lin Min», «Lei Jun» y «4 h 25 min»
    # salían como «asía», «mín» y «leí» sin tilde. Una mayúscula dentro de la
    # oración es un nombre propio y una unidad tras un número no lleva tilde;
    # al inicio de oración o en minúscula, la falta de tilde sigue saliendo.
    body = ("Hizo una estancia en Microsoft Research Asia con Lin Min. La charla duró 4 h 25 min "
            "y habló del libro de Lei Jun. Tambien dijo que la tecnica importa.")
    result = run(str(note(tmp_path, body)))
    for word in ("asia", "min", "lei"):
        assert f"unaccented:{word}" not in result.stdout, result.stdout
    assert "unaccented:tambien" in result.stdout and "unaccented:tecnica" in result.stdout
