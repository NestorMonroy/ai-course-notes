"""El perfil de idioma de las notas: zh (el existente) y es-mx (la traducción).

Los scripts de QA median rasgos didácticos contando etiquetas en chino
(`读图`, `本章小结`, ...). Una nota en español con esos mismos rasgos habría
salido como si no los tuviera: se media el significante, no el significado.
El perfil declara, por idioma, las etiquetas que marcan cada rasgo.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "tools" / "scripts"


def load(name: str):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ES_NOTE = r"""\documentclass{article}
\begin{document}
\section{Tokenización}
En esta sección se explica por qué la tokenización decide el costo del entrenamiento.
\begin{knowledgebox}{Lectura de la figura: la curva de pérdida}
La curva muestra la pérdida por paso.
\end{knowledgebox}
\begin{knowledgebox}{Concepto previo: n-gram}
Un n-gram es una secuencia de n tokens.
\end{knowledgebox}
El docente enfatiza que el vocabulario cambia la longitud de las secuencias.
\subsection{Resumen de la sección}
La tokenización fija la unidad de cómputo.
\section{Síntesis y ampliación}
Cierre.
\end{document}
"""


def test_profile_is_chosen_by_file_name() -> None:
    lang = load("note_language")
    assert lang.for_path("cs336/lecture01/lecture01-notes.tex").code == "zh"
    assert lang.for_path("cs336/lecture01/lecture01-notes.es-mx.tex").code == "es-mx"


def test_zh_profile_keeps_the_existing_markers_and_thresholds() -> None:
    lang = load("note_language")
    zh = lang.ZH
    assert zh.notes_glob == "*-notes.tex"
    assert zh.scaled(260) == 260 and zh.scaled(90) == 90
    assert zh.count("summary", "本章小结 x 总结与延伸") == 2
    assert zh.count("readfig", "读图 怎么看") == 2


def test_es_profile_counts_spanish_markers() -> None:
    lang = load("note_language")
    es = lang.ES_MX
    assert es.notes_glob == "*-notes.es-mx.tex"
    assert es.count("summary", ES_NOTE) == 2
    assert es.count("readfig", ES_NOTE) == 1
    assert es.count("term_digest", ES_NOTE) >= 1
    assert es.count("teacher_voice", ES_NOTE) >= 1
    # Las letras acentuadas cuentan como prosa; el patrón heredado las omitía.
    assert es.prose_chars("tokenización") == len("tokenización")


def test_es_thresholds_are_scaled_from_chinese() -> None:
    lang = load("note_language")
    assert lang.ES_MX.scaled(260) > 260


def test_coverage_counts_spanish_readfig_and_summaries(tmp_path: Path) -> None:
    note = tmp_path / "lecture01-notes.es-mx.tex"
    note.write_text(ES_NOTE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_note_coverage.py"), str(note)],
        capture_output=True, text=True,
    )
    assert "summaries=2" in result.stdout, result.stdout + result.stderr
    assert "readfig=1" in result.stdout
    assert "missing-section-or-final-summary" not in result.stdout


def test_quality_script_finds_and_reads_spanish_notes(tmp_path: Path) -> None:
    note = tmp_path / "lecture01" / "lecture01-notes.es-mx.tex"
    note.parent.mkdir()
    note.write_text(ES_NOTE, encoding="utf-8")
    result = subprocess.run(
        ["bash", str(SCRIPTS / "check_quality.sh"), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert "lecture01-notes.es-mx" in result.stdout, result.stdout + result.stderr
    assert "no-summary" not in result.stdout


def test_structural_audit_accepts_spanish_closing_sections() -> None:
    audit = load("full_quality_audit")
    failures = audit.structural_failures(
        ES_NOTE, "2026-09-25", "Notas", "https://example.com",
        language=load("note_language").ES_MX,
    )
    assert "missing-final-summary" not in failures
    assert not any("summary" in f for f in failures), failures


def test_writing_rules_table_matches_the_profile() -> None:
    """La tabla de etiquetas de las reglas de redacción y el perfil no divergen."""
    lang = load("note_language")
    doc = (REPO_ROOT / "tools/skills/video-render-common/writing-es-mx.md").read_text(encoding="utf-8")
    rows = {}
    for line in doc.splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] in lang.ZH.closing_titles + ("读图", "背景概念", "术语表` / `术语消化", "课堂提示", "老师强调"):
            rows[cells[0]] = cells[1]
    es, zh = lang.ES_MX, lang.ZH
    assert rows[zh.section_summary_title] == es.section_summary_title
    assert rows[zh.final_section_title] == es.final_section_title
    assert rows["拓展阅读"] in es.closing_titles
    assert es.count("readfig_strict", rows["读图"]) == 1
    assert es.count("term_digest", rows["背景概念"]) == 1
    for label in rows["术语表` / `术语消化"].split("` / `"):
        assert es.count("term_digest", label) == 1, label
    assert es.count("teacher_voice", rows["课堂提示"]) == 1
    assert es.count("teacher_voice", rows["老师强调"]) == 1
