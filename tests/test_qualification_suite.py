"""La suite de cualificación de tarea del ciclo es-MX (thyrox TASK-THYROX-0780).

Cada caso es un fragmento real con su traducción aceptada como referencia: las
comprobaciones se derivan del fragmento y sólo exigen lo que la referencia
cumple, para que una traducción correcta pueda aprobar.

Qué haría fallar a esta suite: un caso que no exija los marcadores de respuesta,
que no excluya el chino, que exija una estructura que la referencia no conservó,
que no prohíba las formas prohibidas (también con mayúscula inicial), un patrón
que no compile en JavaScript con la bandera ``u``, o una selección no determinista.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))

import qualification_suite as suite  # noqa: E402

ZH = "\\section{模型}\\label{sec:modelo}\n见图\\ref{fig:a}。\n\\begin{itemize}\n\\item 训练\n\\end{itemize}\n% 注释 \\label{sec:comentada}\n\\includegraphics[width=0.5\\linewidth]{figs/a.png}\n"
ES = "\\section{Modelo}\\label{sec:modelo}\nVer la figura.\n\\begin{itemize}\n\\item Entrenamiento\n\\end{itemize}\n\\includegraphics[width=0.5\\linewidth]{figs/a.png}\n"
FORBIDDEN = [("la regla de oro", None), ("a grandes rasgos", "en general"), ("ver la figura", None)]


def fragment(tmp_path: Path, number: str, zh: str = ZH, es: str | None = ES) -> Path:
    note = tmp_path / "chunks" / "curso__leccion01__notas"
    note.mkdir(parents=True, exist_ok=True)
    zh_path = note / f"{number}.zh.tex"
    zh_path.write_text(zh, encoding="utf-8")
    if es is not None:
        (note / f"{number}.es.tex").write_text(es, encoding="utf-8")
    return zh_path


def checks_of(case: dict) -> list[tuple[str, str]]:
    return [(check["kind"], check.get("text") or check.get("pattern")) for check in case["checks"]]


def test_a_case_demands_the_markers_and_no_chinese(tmp_path: Path) -> None:
    checks = checks_of(suite.case_for(fragment(tmp_path, "000"), "PROMPT", FORBIDDEN))
    assert ("includes", "<<<ES") in checks and ("includes", "ES>>>") in checks
    assert ("excludes-pattern", suite.HAN_PATTERN) in checks


def test_it_demands_only_the_structure_the_reference_kept(tmp_path: Path) -> None:
    checks = checks_of(suite.case_for(fragment(tmp_path, "000"), "PROMPT", FORBIDDEN))
    included = [text for kind, text in checks if kind == "includes"]
    assert "\\label{sec:modelo}" in included and "\\begin{itemize}" in included and "{figs/a.png}" in included
    assert "\\ref{fig:a}" not in included, "la referencia no lo conservó: exigirlo haría la suite inalcanzable"
    assert "\\label{sec:comentada}" not in included, "lo comentado no es estructura"


def test_forbidden_forms_are_excluded_with_either_initial_case(tmp_path: Path) -> None:
    checks = checks_of(suite.case_for(fragment(tmp_path, "000"), "PROMPT", FORBIDDEN))
    patterns = [text for kind, text in checks if kind == "excludes-pattern"]
    assert "[Ll]a regla de oro" in patterns and "[Aa] grandes rasgos" in patterns
    assert not any("er la figura" in pattern for pattern in patterns), "la referencia la usa: no se exige"


def test_patterns_escape_only_what_javascript_unicode_mode_accepts() -> None:
    assert suite.forbidden_pattern("¿qué tal? (o no)") == "¿[Qq]ué tal\\? \\(o no\\)"
    assert "\\ " not in suite.forbidden_pattern("a grandes rasgos")


def test_the_message_carries_the_cycle_prompt_and_the_fragment(tmp_path: Path) -> None:
    zh_path = fragment(tmp_path, "000")
    system, user = suite.case_for(zh_path, "PROMPT", FORBIDDEN)["messages"]
    assert system == {"role": "system", "content": "PROMPT"}
    assert user["role"] == "user" and str(zh_path) in user["content"] and ZH in user["content"]


def test_selection_is_deterministic_and_skips_unusable_fragments(tmp_path: Path) -> None:
    sizes = [400, 800, 1200, 1600, 2000, 2400]
    usable = [fragment(tmp_path, f"{index:03d}", zh="模" * size, es="m" * size) for index, size in enumerate(sizes)]
    fragment(tmp_path, "090", zh="模" * 500, es=None)
    fragment(tmp_path, "091", zh="sin chino " * 50)
    fragment(tmp_path, "092", zh="模" * (suite.MAX_FRAGMENT_CHARS + 1), es="m")
    chosen = suite.select_fragments(tmp_path / "chunks", 3)
    assert chosen == suite.select_fragments(tmp_path / "chunks", 3)
    assert len(chosen) == 3 and set(chosen) <= set(usable)
    assert chosen[0] != chosen[-1]
    assert set(suite.select_fragments(tmp_path / "chunks", 10)) == set(usable), "sin referencia, sin chino o demasiado largo no se elige"


def test_the_suite_declares_its_id_and_class(tmp_path: Path) -> None:
    built = suite.build_suite([fragment(tmp_path, "000")], "PROMPT", FORBIDDEN)
    assert built["id"] == suite.SUITE_ID and built["taskClass"] == "mechanical"
    assert json.loads(json.dumps(built, ensure_ascii=False)) == built
