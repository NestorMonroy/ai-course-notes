"""El sitio de lectura por idioma: zh (el existente) y es-mx.

`generate_site.py` tenia la interfaz en chino escrita en el código, buscaba solo
`*-notes.tex` y tomaba el catalogo de `README.md`. Desde que `README.md` es la
versión es-MX, el sitio zh habría publicado categorías en español: el catalogo
de cada idioma sale de su propio README.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tools" / "web" / "generate_site.py"
HAN = re.compile(r"[一-鿿]")

NOTE = r"""\documentclass{article}
\newcommand{\notetitle}{%s}
\newcommand{\noteauthors}{%s}
\newcommand{\notedate}{2026-01-01}
\newcommand{\videochannel}{Stanford}
\begin{document}
\section{%s}
%s
\end{document}
"""

README_ZH = "# AI Course Notes\n\n### 🏫 Stanford 课程 (1 份)\n\n| 课程 | 主题 | 讲数 | 讲者 |\n|---|---|---|---|\n| [**CS336**](cs336/) | 从零构建语言模型 | 1 | Percy Liang |\n"
README_ES = "# AI Course Notes\n\n### 🏫 Cursos de Stanford (1 notas)\n\n| Curso | Tema | Clases | Docentes |\n|---|---|---|---|\n| [**CS336**](cs336/) | Modelos de lenguaje desde cero | 1 | Percy Liang |\n"


def load_generator():
    name = f"generate_site_{id(object())}"
    spec = importlib.util.spec_from_file_location(name, GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resuelve el modulo por su nombre
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def site_root(tmp_path: Path) -> Path:
    lecture = tmp_path / "cs336" / "lecture01"
    lecture.mkdir(parents=True)
    (lecture / "lecture01-notes.tex").write_text(
        NOTE % ("分词", "基于公开课程资料整理", "分词", "正文。"), encoding="utf-8")
    (lecture / "lecture01-notes.es-mx.tex").write_text(
        NOTE % ("Tokenización", "Elaboradas a partir de materiales públicos", "Tokenización", "Texto."),
        encoding="utf-8")
    (tmp_path / "README.md").write_text(README_ES, encoding="utf-8")
    (tmp_path / "README-zh.md").write_text(README_ZH, encoding="utf-8")
    return tmp_path


def test_each_language_discovers_only_its_notes(site_root: Path) -> None:
    gen = load_generator()
    assert [n.tex_path.name for n in gen.discover_notes(site_root)] == ["lecture01-notes.tex"]
    gen.set_language("es-mx")
    assert [n.tex_path.name for n in gen.discover_notes(site_root)] == ["lecture01-notes.es-mx.tex"]


def test_zh_catalog_comes_from_the_chinese_readme(site_root: Path) -> None:
    """La regresión: con README.md en español, el sitio zh no debe tomar sus categorías."""
    gen = load_generator()
    entries = gen.parse_readme_catalog(site_root)
    assert entries and entries[0].category == "🏫 Stanford 课程 (1 份)"
    assert entries[0].topic == "从零构建语言模型"


def test_es_catalog_comes_from_the_spanish_readme(site_root: Path) -> None:
    gen = load_generator()
    gen.set_language("es-mx")
    entries = gen.parse_readme_catalog(site_root)
    assert entries[0].category == "🏫 Cursos de Stanford (1 notas)"


def test_mkdocs_config_follows_the_language(site_root: Path) -> None:
    gen = load_generator()
    zh = gen.generate_mkdocs_yml(gen.OrderedDict(), {})
    assert "  language: zh" in zh and "  - 首页: index.md" in zh
    gen.set_language("es-mx")
    es = gen.generate_mkdocs_yml(gen.OrderedDict(), {})
    assert "  language: es" in es and "  - Inicio: index.md" in es
    assert "        - es" in es
    assert not HAN.search(es)


def test_every_zh_label_has_an_es_mx_label() -> None:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))
    import note_language
    assert set(note_language.ZH.site_labels) == set(note_language.ES_MX.site_labels)
    assert note_language.ZH.site_labels, "el perfil zh no declara etiquetas del sitio"
    for key, value in note_language.ES_MX.site_labels.items():
        if key.startswith("dir:"):
            continue
        assert not HAN.search(value), f"{key}: {value}"


def test_spanish_site_builds_without_a_chinese_interface(site_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "web-es"
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--lang", "es-mx", "--root", str(site_root),
         "--output", str(out), "--skip-tikz", "--no-compress-images", "--strict"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    page = (out / "docs" / "cs336" / "lecture01" / "index.md").read_text(encoding="utf-8")
    assert "# Tokenización" in page
    assert "Código fuente LaTeX" in page
    index = (out / "docs" / "index.md").read_text(encoding="utf-8")
    assert "Mapa de cursos" in index
    generated = [p for p in (out / "docs").rglob("*.md")] + [out / "mkdocs.yml"]
    offenders = [str(p.relative_to(out)) for p in generated if HAN.search(p.read_text(encoding="utf-8"))]
    assert offenders == [], offenders
