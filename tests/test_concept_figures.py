"""Figuras conceptuales de Zhang Xiaojun: el mismo renderer en zh y en es-MX.

Los 338 PNG llevan el texto chino horneado, asi que la nota traducida no puede
reusarlos. El renderer toma la traduccion de cada cadena de una tabla
(`tools/lang/es-mx/figure_text.tsv`) y escribe `<nombre>.es-mx.png` junto al
original, sin tocarlo.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "render_zhangxiaojun_concept_figures.py"
DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
ONLY = "ep138-vG1RBqn1sG4/figures/chat-to-agent-paradigm.png"


def module():
    spec = importlib.util.spec_from_file_location("concept_figures", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args: str):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO_ROOT)


def table_for(tmp_path: Path, skip: str | None = None) -> Path:
    mod = module()
    spec = next(s for s in mod.SPECS if ONLY in str(s[0]))
    rows = [f"{zh}\tES[{i}]" for i, zh in enumerate(mod.figure_strings([spec])) if zh != skip]
    table = tmp_path / "figure_text.tsv"
    table.write_text("zh\tes_mx\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return table


def test_strings_cover_every_han_text_and_the_footer() -> None:
    mod = module()
    spec = next(s for s in mod.SPECS if ONLY in str(s[0]))
    found = mod.figure_strings([spec])
    assert "从 Chat 到 Agent" in found and "调用工具" in found
    assert mod.FLOW_FOOTER in found
    assert "Tool Use" not in found  # sin chino no hay nada que traducir


def test_es_mx_render_writes_a_sibling_and_leaves_the_original(tmp_path: Path) -> None:
    result = run("--lang", "es-mx", "--table", str(table_for(tmp_path)), "--out-root", str(tmp_path), "--only", ONLY)
    assert result.returncode == 0, result.stderr
    es = tmp_path / "youtube/zhangxiaojun" / ONLY.replace(".png", ".es-mx.png")
    assert es.is_file(), list(tmp_path.rglob("*.png"))
    assert Image.open(es).size == (1600, 960)
    assert not (tmp_path / "youtube/zhangxiaojun" / ONLY).exists()


def test_missing_translation_refuses_without_writing(tmp_path: Path) -> None:
    table = table_for(tmp_path, skip="调用工具")
    result = run("--lang", "es-mx", "--table", str(table), "--out-root", str(tmp_path), "--only", ONLY)
    assert result.returncode == 3
    assert "调用工具" in result.stderr
    assert list(tmp_path.rglob("*.png")) == []


def test_extract_lists_only_the_missing_strings(tmp_path: Path) -> None:
    table = table_for(tmp_path, skip="调用工具")
    result = run("--lang", "es-mx", "--table", str(table), "--only", ONLY, "--extract")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["调用工具"]


def test_zh_keeps_its_paths_and_its_wrapping() -> None:
    # Byte a byte no se puede comparar aqui: el contenedor no tiene ninguna de
    # las fuentes CJK del renderer. Se fija la conducta zh que el cambio toca.
    mod = module()
    mod.configure("zh")
    assert mod.output_path("a/figures/x.png") == "a/figures/x.png"
    assert mod.FONT_PATH in mod.FONT_CANDIDATES
    fnt = ImageFont.truetype(str(DEJAVU), 18)
    assert mod.wrap_text("Lean 代码", fnt, 2000) == ["Lean代码"]


def test_latin_words_keep_their_spaces_in_es_mx() -> None:
    mod = module()
    mod.configure("es-mx")
    fnt = mod.font(18)
    assert mod.wrap_text("la curva de pérdida", fnt, 2000) == ["la curva de pérdida"]


def test_a_title_wider_than_the_canvas_is_shrunk_to_fit() -> None:
    mod = module()
    mod.configure("es-mx")
    title = "Una frase deliberadamente larga que no cabe en el ancho del lienzo a cuarenta y dos puntos"
    size = mod.fit_size(title, 42, mod.W - 156)
    assert size < 42
    assert mod.font(size).getlength(title) <= mod.W - 156
    assert mod.fit_size("Corto", 42, mod.W - 156) == 42


def test_the_table_is_read_without_csv_quoting(tmp_path: Path) -> None:
    # Un rótulo que empieza con comillas no es un campo entrecomillado de CSV.
    mod = module()
    table = tmp_path / "figure_text.tsv"
    table.write_text('zh\tes_mx\n"引号"开头\t"Comillas" al inicio\n', encoding="utf-8")
    assert mod.load_table(table) == {'"引号"开头': '"Comillas" al inicio'}
