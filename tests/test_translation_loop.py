"""El motor del ciclo de traducción: preparar, traducir, ensamblar, verificar
y barrer (`docs/ES_MX_TRANSLATION_PLAN.md`, sección 6).

El traductor real es `headless-pool` de THYROX (un `claude -p` por fragmento).
Aquí lo sustituye un runner falso que hace el mismo contrato de forma
determinista, para probar el ciclo entero sin gastar tokens.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOOP = REPO_ROOT / "tools" / "scripts" / "translation_loop.py"

NOTE = r"""\documentclass{article}
\usepackage[fontset=fandol]{ctex}
\begin{document}
\section{分词}\label{sec:a}
每个 token 都有 embedding。
\begin{knowledgebox}{读图：曲线}
曲线。
\end{knowledgebox}
\section{训练}
训练用 checkpoint。
\[ x = y \]
\subsection{本章小结}
小结。
\end{document}
"""

# Traducción que el runner falso aplica por linea. Un fragmento sin entrada
# aquí se deja con su chino, para ejercitar las señales.
DICTIONARY = {
    "\\section{分词}\\label{sec:a}": "\\section{Tokenización}\\label{sec:a}",
    "每个 token 都有 embedding。": "Cada token tiene su embedding.",
    "\\begin{knowledgebox}{读图：曲线}": "\\begin{knowledgebox}{Lectura de la figura: la curva}",
    "曲线。": "La curva.",
    "\\section{训练}": "\\section{Entrenamiento}",
    "训练用 checkpoint。": "El entrenamiento usa checkpoint.",
    "\\subsection{本章小结}": "\\subsection{Resumen de la sección}",
    "小结。": "Resumen.",
}

FAKE_RUNNER = r'''#!/usr/bin/env python3
# Runner falso: `run headless-pool --prompt P --out O ... < items`. Cada item es
# la ruta del fragmento zh; devuelve la traduccion por diccionario en `result`,
# entre marcadores, como lo hace el `claude -p` real. No escribe el fragmento.
import json, sys
from pathlib import Path
args = sys.argv[1:]
assert args[0] == "headless-pool", args
out = Path(args[args.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
assert args[args.index("--tools") + 1] == "Read,Grep", args
Path(__file__).with_suffix(".args").write_text(json.dumps(args))
table = json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf-8"))
items = [l for l in sys.stdin.read().splitlines() if l.strip()]
index = []
for n, zh in enumerate(items, 1):
    assert "\t" not in zh
    index.append(f"{n}\t{zh}")
    lines = [table.get(l, l) for l in Path(zh).read_text(encoding="utf-8").splitlines()]
    body = "\n".join(lines)
    result = "SIN MARCADORES" if "OMITIR" in body else f"Listo.\n<<<ES\n{body}\nES>>>\n"
    (out / f"{n}.json").write_text(json.dumps({"is_error": False, "result": result, "total_cost_usd": 0.5,
                                               "duration_ms": 1000,
                                               "usage": {"input_tokens": 10, "output_tokens": 20,
                                                         "cache_creation_input_tokens": 100,
                                                         "cache_read_input_tokens": 50}}))
(out / "index.tsv").write_text("\n".join(index) + "\n", encoding="utf-8")
print(f"items={len(items)} ok={len(items)} fallidos=0")
'''


def setup(tmp_path: Path, dictionary=DICTIONARY, source: str = NOTE) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    note = repo / "cs000" / "lecture01" / "lecture01-notes.tex"
    note.parent.mkdir(parents=True)
    note.write_text(source, encoding="utf-8")
    runner = tmp_path / "fake_run.py"
    runner.write_text(FAKE_RUNNER, encoding="utf-8")
    runner.chmod(0o755)
    runner.with_suffix(".json").write_text(json.dumps(dictionary, ensure_ascii=False), encoding="utf-8")
    return repo, note, runner


def loop(repo: Path, *args: str, runner: Path | None = None, cache: Path | None = None):
    env = dict(os.environ)
    if runner:
        env["TRANSLATION_RUNNER"] = str(runner)
    if cache:
        env["THYROX_CACHE_DIR"] = str(cache)
    return subprocess.run([sys.executable, str(LOOP), *args], cwd=repo, env=env, capture_output=True, text=True)


def test_prepare_splits_the_body_into_section_chunks(tmp_path: Path) -> None:
    repo, note, _ = setup(tmp_path)
    bench = tmp_path / "bench"
    result = loop(repo, "prepare", "--bench", str(bench), str(note))
    assert result.returncode == 0, result.stderr
    units = (bench / "units.tsv").read_text(encoding="utf-8").splitlines()
    assert len(units) == 3, units  # portada vacía + 2 secciones
    head = (bench / "chunks" / "cs000__lecture01__lecture01-notes" / "head.tex").read_text(encoding="utf-8")
    assert "polyglossia" in head and "ctex" not in head


def test_full_cycle_with_the_fake_translator_is_clean(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    assert loop(repo, "prepare", "--bench", str(bench), str(note)).returncode == 0
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 0, result.stderr
    assert loop(repo, "assemble", "--bench", str(bench)).returncode == 0
    es = note.with_name("lecture01-notes.es-mx.tex")
    text = es.read_text(encoding="utf-8")
    assert "\\section{Tokenización}" in text and "\\setdefaultlanguage[variant=mexican]{spanish}" in text
    out = bench / "signals.jsonl"
    verify = loop(repo, "verify", "--out", str(out), str(es), cache=tmp_path / "cache")
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert out.read_text(encoding="utf-8").strip() == ""


def test_verify_reports_untranslated_chunks_and_uses_the_cache(tmp_path: Path) -> None:
    partial = {k: v for k, v in DICTIONARY.items() if "训练" not in k}
    repo, note, runner = setup(tmp_path, partial)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    loop(repo, "assemble", "--bench", str(bench))
    es = note.with_name("lecture01-notes.es-mx.tex")
    cache = tmp_path / "cache"
    first = loop(repo, "verify", "--out", str(bench / "s1.jsonl"), str(es), cache=cache)
    assert first.returncode == 1
    rows = [json.loads(l) for l in (bench / "s1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "parity:residual-han" in {r["signal"] for r in rows}
    second = loop(repo, "verify", "--out", str(bench / "s2.jsonl"), str(es), cache=cache)
    assert "cache: 1 de 1" in second.stderr
    assert (bench / "s1.jsonl").read_text() == (bench / "s2.jsonl").read_text()


def test_coverage_reports_only_what_the_translation_broke(tmp_path: Path) -> None:
    # El original ya tiene pocas cajas y le falta el resumen: esa deuda es del
    # original y no de la traducción. Perder el caption del listado, en cambio,
    # lo rompe la traducción y tiene que salir.
    listing_zh = "\\begin{lstlisting}[caption=训练循环]"
    source = NOTE.replace("\\[ x = y \\]", listing_zh + "\nx = 1\n\\end{lstlisting}")
    dictionary = dict(DICTIONARY, **{listing_zh: "\\begin{lstlisting}"})
    repo, note, runner = setup(tmp_path, dictionary, source)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    loop(repo, "assemble", "--bench", str(bench))
    es = note.with_name("lecture01-notes.es-mx.tex")
    out = bench / "signals.jsonl"
    loop(repo, "verify", "--out", str(out), str(es), cache=tmp_path / "cache")
    signals = {json.loads(l)["signal"] for l in out.read_text(encoding="utf-8").splitlines()}
    assert "coverage:code-blocks-without-captions" in signals, signals
    assert "coverage:too-few-teaching-boxes" not in signals
    assert "coverage:missing-section-or-final-summary" not in signals


def test_translate_skips_chunks_already_clean(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    again = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert "0 fragmento(s) por traducir" in again.stderr, again.stderr


def test_translate_refuses_a_model_alias(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "sonnet", runner=runner)
    assert result.returncode == 2 and "identificador completo" in result.stderr


def test_sweep_applies_a_mechanical_fix_everywhere_and_records_it(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    loop(repo, "assemble", "--bench", str(bench))
    es = note.with_name("lecture01-notes.es-mx.tex")
    es.write_text(es.read_text(encoding="utf-8").replace("Resumen.", "La regla de oro."), encoding="utf-8")
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({
        "patron": "cliche en el resumen",
        "senal_del_verificador": "prose:forbidden:regla de oro",
        "fix_generico": {"tipo": "mechanical", "buscar": "La regla de oro.", "reemplazar": "Resumen."},
        "archivos_donde_ya_se_aplico": [],
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    result = loop(repo, "sweep", "--bench", str(bench), "--iteration", "1", "--memory", str(memory),
                  cache=tmp_path / "cache")
    assert result.returncode == 0, result.stderr
    assert "La regla de oro." not in es.read_text(encoding="utf-8")
    sweep = [json.loads(l) for l in (bench / "sweep.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sweep[0]["iteration"] == 1 and sweep[0]["instancias"] == 1 and sweep[0]["notas_revisadas"] == 1
    entry = json.loads(memory.read_text(encoding="utf-8"))
    assert str(es.relative_to(repo)) in entry["archivos_donde_ya_se_aplico"]


def test_prompt_carries_the_glossary_and_the_memory_rules(tmp_path: Path) -> None:
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({
        "patron": "x", "senal_del_verificador": "parity:keep-term:checkpoint",
        "fix_generico": {"tipo": "prompt", "regla": "REGLA-DE-PRUEBA: checkpoint se queda en ingles"},
        "archivos_donde_ya_se_aplico": ["a"],
    }) + "\n", encoding="utf-8")
    out = tmp_path / "prompt.md"
    result = loop(REPO_ROOT, "prompt", "--memory", str(memory), "--out", str(out))
    assert result.returncode == 0, result.stderr
    text = out.read_text(encoding="utf-8")
    assert "REGLA-DE-PRUEBA" in text
    assert "embedding" in text and "imbibición" in text
    assert "Resumen de la sección" in text


def load_loop():
    import importlib.util
    spec = importlib.util.spec_from_file_location("translation_loop", LOOP)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LOOP.parent))
    spec.loader.exec_module(mod)
    return mod


def test_memory_is_bounded_by_memfree_and_width_is_only_a_ceiling(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 0, result.stderr
    args = json.loads(runner.with_suffix(".args").read_text())
    # La memoria la hace cumplir GNU Parallel mientras el pool corre; la
    # anchura no depende de la carga, que mide a otros procesos.
    assert args[args.index("--memfree") + 1] == "3G"
    assert args[args.index("--width") + 1] == "10"
    other = tmp_path / "bench2"
    loop(repo, "prepare", "--bench", str(other), str(note))
    loop(repo, "translate", "--bench", str(other), "--model", "claude-sonnet-5", "--width", "2",
         "--memfree", "1G", runner=runner)
    args = json.loads(runner.with_suffix(".args").read_text())
    assert args[args.index("--width") + 1] == "2" and args[args.index("--memfree") + 1] == "1G"


def test_a_result_without_markers_leaves_the_chunk_pending(tmp_path: Path) -> None:
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "OMITIR"})
    repo, note, runner = setup(tmp_path, dictionary)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 1
    assert "sin marcadores" in result.stderr
    written = sorted(p.name for p in bench.rglob("*.es.tex"))
    pending = [l for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines()]
    assert len(written) == len(pending) - 1


def test_a_chunk_without_han_is_copied_without_the_model(tmp_path: Path) -> None:
    source = NOTE.replace("\\section{训练}", "\\section{Setup}\nEnglish only.\n\\section{训练}")
    repo, note, runner = setup(tmp_path, source=source)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    units = (bench / "units.tsv").read_text(encoding="utf-8").splitlines()
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 0, result.stderr
    items = (next(bench.rglob("index.tsv"))).read_text(encoding="utf-8").splitlines()
    plain = [u for u in units if not any("\u4e00" <= ch <= "\u9fff" for ch in Path(u.split("\t")[3]).read_text())]
    assert any("English only." in Path(u.split("\t")[3]).read_text() for u in plain)
    assert len(items) == len(units) - len(plain)
    assert f"sin chino: {len(plain)}" in result.stderr
    for u in plain:
        zh, es = u.split("\t")[3:5]
        assert Path(es).read_text() == Path(zh).read_text()


def test_usage_sums_tokens_by_component_and_measures_letters_per_han(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    items = len(next(bench.rglob("index.tsv")).read_text(encoding="utf-8").splitlines())
    result = loop(repo, "usage", "--bench", str(bench))
    assert result.returncode == 0, result.stderr
    totals = dict(kv.split("=") for kv in result.stdout.split())
    assert int(totals["items"]) == items
    # Los cuatro componentes por separado, como THYROX (`transcript/usage.py`):
    # el peso de cada uno es del contrato de precio, no del ciclo.
    assert int(totals["input"]) == 10 * items and int(totals["output"]) == 20 * items
    assert int(totals["cache_creation"]) == 100 * items and int(totals["cache_read"]) == 50 * items
    assert not any("cost" in k or "usd" in k for k in totals)
    assert float(totals["letters_per_han"]) > 0
    rows = (bench / "usage.tsv").read_text(encoding="utf-8").splitlines()
    assert rows[0].split("\t") == ["chunk", "han", "letters", "input", "cache_creation", "cache_read", "output",
                                   "peak_rss_kb", "wall_s", "cpu_s"]
    assert len(rows) == items + 1


def test_english_the_original_already_uses_is_not_a_translation_defect(tmp_path: Path) -> None:
    # La nota zh ya escribe `reward model` en inglés: es término técnico que se
    # queda. `weights` no esta en el original: lo introdujo la traducción.
    source = NOTE.replace("小结。", "小结：reward model 和 worker 追求 precision。")
    dictionary = dict(DICTIONARY, **{"小结：reward model 和 worker 追求 precision。":
                                     "Resumen: el reward model y los workers buscan precision, igual que los weights."})
    repo, note, runner = setup(tmp_path, dictionary, source)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    loop(repo, "assemble", "--bench", str(bench))
    out = bench / "signals.jsonl"
    loop(repo, "verify", "--out", str(out), str(note.with_name("lecture01-notes.es-mx.tex")), cache=tmp_path / "cache")
    signals = {json.loads(l)["signal"] for l in out.read_text(encoding="utf-8").splitlines()}
    assert "prose:english:weights" in signals, signals
    assert "prose:english:reward" not in signals and "prose:english:model" not in signals
    # El plural inglés de un término del original sigue siendo ese término.
    assert "prose:english:workers" not in signals
    # `precision` en inglés viene del original: no es «precisión» sin tilde.
    assert "prose:unaccented:precision" not in signals


def test_compile_reports_an_error_even_when_a_pdf_comes_out(tmp_path: Path) -> None:
    # En nonstopmode XeLaTeX se recupera de un error y aun escribe el PDF; el
    # veredicto sale del error, no de que exista el archivo.
    mod = load_loop()
    broken = tmp_path / "broken.es-mx.tex"
    broken.write_text("\\documentclass{article}\n\\begin{document}\nhola\\newpage\nadios\\newpage\n\\undefinedcmd hola\n\\end{document}\n")
    signals = mod.compile_signal(broken)
    assert signals and signals[0][0] == "compile:error" and "Undefined control sequence" in signals[0][1]
    clean = tmp_path / "clean.es-mx.tex"
    clean.write_text("\\documentclass{article}\n\\begin{document}\nhola\n\\end{document}\n")
    assert mod.compile_signal(clean) == []


def test_chinese_in_the_head_is_translated_as_its_own_unit(tmp_path: Path) -> None:
    title_zh = "\\newcommand{\\notetitle}{分词笔记}"
    source = NOTE.replace("\\begin{document}", title_zh + "\n\\begin{document}", 1)
    dictionary = dict(DICTIONARY, **{title_zh: "\\newcommand{\\notetitle}{Notas de tokenización}"})
    repo, note, runner = setup(tmp_path, dictionary, source)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    assert any("\thead\t" in l for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines())
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert loop(repo, "assemble", "--bench", str(bench)).returncode == 0
    text = note.with_name("lecture01-notes.es-mx.tex").read_text(encoding="utf-8")
    assert "\\newcommand{\\notetitle}{Notas de tokenización}" in text and "分词" not in text
    assert "\\setdefaultlanguage[variant=mexican]{spanish}" in text


def test_compile_reports_glyphs_the_font_does_not_have(tmp_path: Path) -> None:
    mod = load_loop()
    tex = tmp_path / "glyph.es-mx.tex"
    tex.write_text("\\documentclass{article}\n\\begin{document}\nTitulo 自我\n\\end{document}\n", encoding="utf-8")
    signals = mod.compile_signal(tex)
    assert [s for s, _ in signals] == ["compile:missing-glyph"], signals


def test_cycle_chains_prepare_translate_assemble_and_verify(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    result = loop(repo, "cycle", "--bench", str(bench), "--model", "claude-sonnet-5", str(note),
                  runner=runner, cache=tmp_path / "cache")
    assert result.returncode == 0, result.stdout + result.stderr
    assert note.with_name("lecture01-notes.es-mx.tex").is_file()
    assert (bench / "iterations" / "01" / "signals.jsonl").read_text(encoding="utf-8").strip() == ""
    assert (bench / "iterations" / "01" / "usage.tsv").is_file()


def test_cycle_stops_before_assembling_when_a_chunk_is_missing(tmp_path: Path) -> None:
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "OMITIR"})
    repo, note, runner = setup(tmp_path, dictionary)
    bench = tmp_path / "bench"
    result = loop(repo, "cycle", "--bench", str(bench), "--model", "claude-sonnet-5", str(note),
                  runner=runner, cache=tmp_path / "cache")
    assert result.returncode == 1
    assert "sin marcadores" in result.stderr
    # La negativa es declarada, no un traceback: un choque también dejaría sin nota.
    assert "falta el fragmento traducido" in result.stderr and "Traceback" not in result.stderr
    assert not note.with_name("lecture01-notes.es-mx.tex").exists()


def test_assemble_points_to_the_es_mx_figure_when_it_exists(tmp_path: Path) -> None:
    source = NOTE.replace("曲线。", "曲线。\n\\includegraphics[width=0.8\\linewidth]{figures/curve.png}\n"
                                    "\\includegraphics{figures/slide.png}")
    repo, note, runner = setup(tmp_path, source=source)
    figures = note.parent / "figures"
    figures.mkdir()
    for name in ("curve.png", "curve.es-mx.png", "slide.png"):
        (figures / name).write_bytes(b"png")
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert loop(repo, "assemble", "--bench", str(bench)).returncode == 0
    es = note.with_name("lecture01-notes.es-mx.tex")
    text = es.read_text(encoding="utf-8")
    # La figura con texto horneado tiene hermana es-MX; la captura sin ella se queda.
    assert "{figures/curve.es-mx.png}" in text and "{figures/slide.png}" in text
    out = bench / "signals.jsonl"
    loop(repo, "verify", "--out", str(out), str(es), cache=tmp_path / "cache")
    assert "parity:images" not in out.read_text(encoding="utf-8")


def test_each_cycle_run_is_a_new_iteration_and_nothing_is_overwritten(tmp_path: Path) -> None:
    # El plan (secciones 6 y 7) pide el registro de CADA iteración en el banco
    # del lote, versionado: un lote se audita iteración por iteración. Un
    # `signals.jsonl` único por banco se sobrescribía en cada ejecución.
    partial = {k: v for k, v in DICTIONARY.items() if "训练" not in k}
    repo, note, runner = setup(tmp_path, partial)
    workbench = repo / ".claude" / "workbench"
    first = loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
                 runner=runner, cache=tmp_path / "cache")
    assert first.returncode == 1  # quedó chino: hay señales
    runner.with_suffix(".json").write_text(json.dumps(DICTIONARY, ensure_ascii=False), encoding="utf-8")
    bench = workbench / "translation" / "cs000"
    for chunk in bench.rglob("*.es.tex"):
        chunk.unlink()  # el paso de retraducción de este control
    second = loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
                  runner=runner, cache=tmp_path / "cache")
    assert second.returncode == 0, second.stdout + second.stderr
    one, two = bench / "iterations" / "01", bench / "iterations" / "02"
    assert (one / "signals.jsonl").read_text(encoding="utf-8").strip() != ""
    assert (two / "signals.jsonl").read_text(encoding="utf-8").strip() == ""
    assert (one / "usage.tsv").is_file() and (two / "usage.tsv").is_file()
    rows = (workbench / "translation" / "batches.tsv").read_text(encoding="utf-8").splitlines()
    header = rows[0].split("\t")
    assert header[:4] == ["batch", "iteration", "started", "notes"]
    runs = [dict(zip(header, r.split("\t"))) for r in rows[1:]]
    assert [(r["batch"], r["iteration"]) for r in runs] == [("cs000", "01"), ("cs000", "02")]
    assert int(runs[0]["signals"]) > 0 and runs[1]["signals"] == "0"
    # El puntero al lote en curso lo escribe el ciclo y se versiona: dice dónde
    # estamos; `batches.tsv` dice cómo se llegó.
    assert (workbench / ".last-bank").read_text(encoding="utf-8").strip() == ".claude/workbench/translation/cs000"


def test_retranslate_marks_only_the_chunks_that_carry_the_signal(tmp_path: Path) -> None:
    # Paso 3 del plan: corregida la causa raíz (la plantilla), se retraducen
    # los fragmentos que llevan la señal y ningún otro.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El training usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    first = loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
                 runner=runner, cache=tmp_path / "cache")
    assert first.returncode == 1
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    chunks = sorted(bench.rglob("*.es.tex"))
    carrying = [c for c in chunks if "training" in c.read_text(encoding="utf-8")]
    assert len(carrying) == 1 and len(chunks) > 1
    result = loop(repo, "retranslate", "--batch", "cs000")
    assert result.returncode == 0, result.stderr
    assert not carrying[0].exists()
    assert all(c.exists() for c in chunks if c != carrying[0])
    listed = (bench / "iterations" / "01" / "retranslate.tsv").read_text(encoding="utf-8")
    assert "prose:english:training" in listed and carrying[0].name in listed


def test_plan_groups_notes_by_course_in_ascending_size(tmp_path: Path) -> None:
    # Fase 3 del plan: un curso por lote, del más pequeño al más grande (`zz1`
    # va primero aunque el alfabeto diga lo contrario). El
    # plan se deriva del repositorio y queda versionado; no se arma a mano.
    repo = tmp_path / "repo"
    small = [repo / "zz1" / f"lecture0{i}" / f"lecture0{i}-notes.tex" for i in (1, 2)]
    big = [repo / "talks" / "lab" / "sp25" / "lecture01" / "lecture01-notes.tex"]
    for path, size in [(small[0], 10), (small[1], 10), (big[0], 500)]:
        path.parent.mkdir(parents=True)
        path.write_text("x" * size, encoding="utf-8")
    (small[0].with_name("lecture01-notes.es-mx.tex")).write_text("ya traducida", encoding="utf-8")
    result = loop(repo, "plan", "--out", ".claude/workbench/translation/plan.tsv")
    assert result.returncode == 0, result.stderr
    rows = (repo / ".claude/workbench/translation/plan.tsv").read_text(encoding="utf-8").splitlines()
    assert rows[0].split("\t") == ["order", "batch", "bytes", "notes", "paths"]
    first, second = (r.split("\t") for r in rows[1:])
    assert first[:4] == ["1", "zz1", "20", "2"]
    assert first[4].split(" ") == ["zz1/lecture01/lecture01-notes.tex", "zz1/lecture02/lecture02-notes.tex"]
    assert second[:4] == ["2", "talks__lab__sp25", "500", "1"]


def test_an_undefined_command_is_located_in_its_chunk(tmp_path: Path) -> None:
    # Fase 2: `\enquote` sin cargar csquotes. La señal de compilación solo
    # guardaba «! Undefined control sequence.»; el comando está en la línea
    # `l.NN` siguiente del log, y sin él no se sabe qué fragmento retraducir.
    mod = load_loop()
    broken = tmp_path / "broken.es-mx.tex"
    broken.write_text("\\documentclass{article}\n\\begin{document}\nhola\\newpage\n"
                      "la respuesta \\enquote{correcta}\n\\end{document}\n", encoding="utf-8")
    (signal, detail), = mod.compile_signal(broken)
    assert signal == "compile:error" and "\\enquote" in detail, detail
    repo, note, runner = setup(tmp_path / "loop")
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
         runner=runner, cache=tmp_path / "cache")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    chunks = sorted(bench.rglob("*.es.tex"))
    chunks[-1].write_text(chunks[-1].read_text(encoding="utf-8") + "\\enquote{x}\n", encoding="utf-8")
    es_note = note.with_name("lecture01-notes.es-mx.tex")
    (bench / "iterations" / "01" / "signals.jsonl").write_text(json.dumps(
        {"note": "cs000/lecture01/lecture01-notes.es-mx.tex", "signal": "compile:error", "detail": detail}) + "\n",
        encoding="utf-8")
    assert loop(repo, "retranslate", "--batch", "cs000").returncode == 0
    assert not chunks[-1].exists() and all(c.exists() for c in chunks[:-1])


def test_a_readfig_error_is_inherited_when_the_original_has_no_strict_marker(tmp_path: Path) -> None:
    # cs329a/lecture02: el original pasa `readfig` por una coincidencia
    # («完整图景……说明»), no por explicar sus figuras. Con el marcador estricto,
    # que tiene equivalente exacto (读图 ↔ «Lectura de la figura»), el defecto
    # es del original y no de la traducción.
    figures = "".join(f"\\begin{{figure}}\\includegraphics{{f{i}.png}}\\caption{{图{i}}}\\end{{figure}}\n" for i in range(3))
    source = NOTE.replace("\\begin{knowledgebox}{读图：曲线}\n曲线。\n\\end{knowledgebox}\n",
                          figures + "本讲建立了完整图景，说明了方法。\n")
    dictionary = dict(DICTIONARY, **{f"\\begin{{figure}}\\includegraphics{{f{i}.png}}\\caption{{图{i}}}\\end{{figure}}":
                                     f"\\begin{{figure}}\\includegraphics{{f{i}.png}}\\caption{{Figura {i}}}\\end{{figure}}"
                                     for i in range(3)},
                      **{"本讲建立了完整图景，说明了方法。": "La clase construyó el panorama completo y explicó el método."})
    repo, note, runner = setup(tmp_path, dictionary, source)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
         runner=runner, cache=tmp_path / "cache")
    signals = (repo / ".claude/workbench/translation/cs000/iterations/01/signals.jsonl").read_text(encoding="utf-8")
    assert "figures-present-but-no-readfig-explanation" not in signals, signals


def test_a_verifier_that_dies_is_an_incomplete_verdict_not_a_clean_one(tmp_path: Path) -> None:
    # cs329a, iteración 02: un `verify-one` murió y `run_verify` leyó «sin
    # filas» como «sin señales». Una nota sin veredicto nunca cuenta como limpia.
    repo, note, runner = setup(tmp_path)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
         runner=runner, cache=tmp_path / "cache")
    es = note.with_name("lecture01-notes.es-mx.tex")
    orphan = repo / "cs001" / "lecture01" / "lecture01-notes.es-mx.tex"
    orphan.parent.mkdir(parents=True)
    orphan.write_text(es.read_text(encoding="utf-8"), encoding="utf-8")  # sin original zh: el verificador muere
    out = tmp_path / "signals.jsonl"
    result = loop(repo, "verify", "--out", str(out), str(es), str(orphan), cache=tmp_path / "cache2")
    assert result.returncode == 2, result.stdout + result.stderr
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    incomplete = {r["note"] for r in rows if r["signal"] == "verify:incomplete"}
    assert "cs001/lecture01/lecture01-notes.es-mx.tex" in incomplete
    assert "incompleta" in result.stderr


def test_prompt_cites_every_prohibited_form(tmp_path: Path) -> None:
    # cs329a, iteración 02: «la clave está en» sobrevivió a la retraducción; la
    # plantilla solo citaba tres clichés de ejemplo y no la lista entera.
    repo, _note, _runner = setup(tmp_path)
    out = tmp_path / "prompt.md"
    assert loop(repo, "prompt", "--out", str(out)).returncode == 0
    prompt = out.read_text(encoding="utf-8")
    forms = [l.split("→")[0].split("->")[0].strip()
             for l in (REPO_ROOT / "tools/lang/es-mx/prohibited_forms.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    assert "la clave está en" in forms
    missing = [f for f in forms if f"`{f}`" not in prompt]
    assert not missing, missing[:5]


def test_a_signal_inside_a_hyphenated_word_is_located_and_none_vanishes(tmp_path: Path) -> None:
    # cs329a, iteración 03: `hard` y `coding` salen de «hard-coding»; el patrón
    # no cruzaba el guion y la señal desaparecía de la lista sin ir a juicio.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El modelo hace hard-coding del checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
         runner=runner, cache=tmp_path / "cache")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    signals = bench / "iterations" / "01" / "signals.jsonl"
    rows = [json.loads(l) for l in signals.read_text(encoding="utf-8").splitlines()]
    rows.append({"note": rows[0]["note"], "signal": "prose:english:inexistente", "detail": ""})
    signals.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert loop(repo, "retranslate", "--batch", "cs000").returncode == 0
    listed = (bench / "iterations" / "01" / "retranslate.tsv").read_text(encoding="utf-8").splitlines()[1:]
    by_signal = {l.split("\t")[0]: l.split("\t")[3] for l in listed}
    assert by_signal.get("prose:english:hard") == "retranslate", listed
    assert by_signal.get("prose:english:inexistente") == "manual"
    assert len(listed) >= len(rows)


def test_a_chunk_that_breaks_the_environments_is_rejected_on_arrival(tmp_path: Path) -> None:
    # cs329a, iteración 04: un fragmento retraducido volvió sin un
    # `\begin{itemize}` y la nota dejó de compilar. Se rechaza al recibirlo.
    source = NOTE.replace("训练用 checkpoint。", "\\begin{itemize}\n\\item 训练用 checkpoint。\n\\end{itemize}")
    dictionary = dict(DICTIONARY, **{"\\begin{itemize}": "", "\\item 训练用 checkpoint。": "\\item El entrenamiento usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary, source)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 1
    assert "estructura" in result.stderr and "itemize" in result.stderr
    broken = [u.split("\t") for u in (bench / "units.tsv").read_text(encoding="utf-8").splitlines()
              if "itemize" in Path(u.split("\t")[3]).read_text(encoding="utf-8")]
    assert broken and not Path(broken[0][4]).exists()


def test_retranslate_also_sends_back_chunks_already_written_with_a_broken_structure(tmp_path: Path) -> None:
    # El fragmento que rompió `itemize` en cs329a se escribió antes de que
    # `translate` revisara los entornos; su señal de compilación no nombra un
    # comando, así que solo se encuentra comparando su estructura con el original.
    source = NOTE.replace("训练用 checkpoint。", "\\begin{itemize}\n\\item 训练用 checkpoint。\n\\end{itemize}")
    repo, note, runner = setup(tmp_path, DICTIONARY, source)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    target = next(c for c in bench.rglob("*.es.tex") if "itemize" in c.read_text(encoding="utf-8"))
    target.write_text(target.read_text(encoding="utf-8").replace("\\begin{itemize}\n", ""), encoding="utf-8")
    assert loop(repo, "retranslate", "--batch", "cs000").returncode == 0
    assert not target.exists()
    listed = (bench / "iterations" / "01" / "retranslate.tsv").read_text(encoding="utf-8")
    assert "structure:itemize" in listed


def test_prepare_links_the_english_source_and_not_a_chinese_one(tmp_path: Path) -> None:
    # Las notas zh traducen clases dadas en inglés; la transcripción original
    # dice qué término usó quien habló. Se enlaza, no se copia: son 64.7 MB.
    repo, note, _runner = setup(tmp_path)
    (note.parent / "lecture01.en.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nthe model pool\n",
                                                  encoding="utf-8")
    other = repo / "cs001" / "lecture01" / "lecture01-notes.tex"
    other.parent.mkdir(parents=True)
    other.write_text(NOTE, encoding="utf-8")
    (other.parent / "lecture01.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\n模型池的训练\n", encoding="utf-8")
    bench = tmp_path / "bench"
    assert loop(repo, "prepare", "--bench", str(bench), str(note), str(other)).returncode == 0
    link = bench / "chunks" / "cs000__lecture01__lecture01-notes" / "source.srt"
    assert link.is_symlink() and not Path(os.readlink(link)).is_absolute()
    assert "model pool" in link.read_text(encoding="utf-8")
    assert not (bench / "chunks" / "cs001__lecture01__lecture01-notes" / "source.srt").exists()


def test_the_prompt_says_when_to_consult_the_english_source(tmp_path: Path) -> None:
    repo, _note, _runner = setup(tmp_path)
    out = tmp_path / "prompt.md"
    loop(repo, "prompt", "--out", str(out))
    text = out.read_text(encoding="utf-8")
    assert "source.srt" in text and "Grep" in text


def test_a_mechanical_fix_lands_in_the_chunks_and_survives_the_next_assemble(tmp_path: Path) -> None:
    # Ruta 1 (determinista) del plan v3: se aplica por texto, sin esperar una
    # señal (la del glifo solo sale compilando), y en los fragmentos, que son la
    # fuente de verdad: un arreglo solo en la nota lo deshacía el siguiente ensamblado.
    dictionary = dict(DICTIONARY, **{"小结。": "Resumen （breve）: la clave está en los datos."})
    repo, note, runner = setup(tmp_path, dictionary)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    memory = tmp_path / "memory.jsonl"
    memory.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in [
        {"patron": "paréntesis de ancho completo", "senal_del_verificador": "compile:missing-glyph",
         "fix_generico": {"tipo": "mechanical", "buscar": "（", "reemplazar": "("}, "archivos_donde_ya_se_aplico": []},
        {"patron": "paréntesis de ancho completo", "senal_del_verificador": "compile:missing-glyph",
         "fix_generico": {"tipo": "mechanical", "buscar": "）", "reemplazar": ")"}, "archivos_donde_ya_se_aplico": []},
        {"patron": "cliché", "senal_del_verificador": "prose:forbidden:la clave está en",
         "fix_generico": {"tipo": "mechanical", "buscar": "la clave está en", "reemplazar": "lo esencial está en"},
         "archivos_donde_ya_se_aplico": []}]), encoding="utf-8")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    result = loop(repo, "sweep", "--bench", str(bench), "--iteration", "1", "--memory", str(memory), cache=tmp_path / "c")
    assert result.returncode == 0, result.stderr
    assert loop(repo, "assemble", "--bench", str(bench)).returncode == 0
    text = note.with_name("lecture01-notes.es-mx.tex").read_text(encoding="utf-8")
    assert "Resumen (breve): lo esencial está en los datos." in text, text[-200:]
    log = [json.loads(l) for l in (bench / "sweep.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["aplicadas"] for r in log] == [1, 1, 1]


def test_triage_routes_signals_and_retranslate_only_takes_the_local_ones(tmp_path: Path) -> None:
    # Plan v3: clasificar antes de asignar. `throughput` en dos notas de dos
    # lotes es una causa compartida (se decide una vez: glosario, plantilla o
    # verificador); `weights` en una sola nota es local (se retraduce); la forma
    # prohibida con arreglo mecánico en memoria es determinista.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El throughput usa checkpoint.",
                                     "权重。": "Los weights y la clave está en ellos."})
    repo, note, runner = setup(tmp_path, dictionary)
    other = repo / "cs001" / "lecture01" / "lecture01-notes.tex"
    other.parent.mkdir(parents=True)
    other.write_text(NOTE.replace("小结。", "小结。\n权重。"), encoding="utf-8")
    for batch, path in (("cs000", note), ("cs001", other)):
        loop(repo, "cycle", "--batch", batch, "--model", "claude-sonnet-5", str(path), runner=runner, cache=tmp_path / "c")
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({"patron": "cliché", "senal_del_verificador": "prose:forbidden:la clave está en",
                                  "fix_generico": {"tipo": "mechanical", "buscar": "la clave está en",
                                                   "reemplazar": "lo esencial está en"},
                                  "archivos_donde_ya_se_aplico": []}, ensure_ascii=False) + "\n", encoding="utf-8")
    result = loop(repo, "triage", "--memory", str(memory))
    assert result.returncode == 0, result.stderr
    rows = [dict(zip(["route", "signal", "notes", "paths"], l.split("\t")))
            for l in (repo / ".claude/workbench/translation/triage.tsv").read_text(encoding="utf-8").splitlines()[1:]]
    route = {r["signal"]: r["route"] for r in rows}
    assert route["prose:english:throughput"] == "shared" and route["prose:english:weights"] == "local"
    assert route["prose:forbidden:la clave está en"] == "deterministic"
    assert rows[0]["route"] == "deterministic" and rows[1]["signal"] == "prose:english:throughput"
    bench = repo / ".claude/workbench/translation/cs001"
    loop(repo, "retranslate", "--batch", "cs001", "--memory", str(memory))
    listed = {l.split("\t")[0]: l.split("\t")[3] for l in
              (bench / "iterations/01/retranslate.tsv").read_text(encoding="utf-8").splitlines()[1:]}
    assert listed["prose:english:weights"] == "retranslate"
    assert listed["prose:english:throughput"] == "shared"
    assert listed["prose:forbidden:la clave está en"] == "deterministic"


def test_the_verdict_cache_changes_when_any_verifier_input_changes(tmp_path: Path) -> None:
    # El caché de veredictos se reusaba aunque cambiaran las frases fijas o el
    # diccionario es_MX: sus archivos no entraban en la huella.
    import shutil
    mod = load_loop()
    lang = tmp_path / "es-mx"
    shutil.copytree(mod.LANG_DIR, lang, symlinks=True)
    mod.LANG_DIR = lang
    for name in ("phrases.tsv", "glossary.tsv", "prohibited_forms.txt", "hunspell/es_MX.dic", "hunspell/es_MX.aff"):
        before = mod.fingerprint(False)
        with (lang / name).open("a", encoding="utf-8") as handle:
            handle.write("\n")
        assert mod.fingerprint(False) != before, name


def test_the_prompt_carries_the_fixed_phrases(tmp_path: Path) -> None:
    repo, _note, _runner = setup(tmp_path)
    out = tmp_path / "prompt.md"
    loop(repo, "prompt", "--out", str(out))
    assert "`自我改进 AI Agent` → `Agentes de IA que se automejoran`" in out.read_text(encoding="utf-8")


def test_the_sweep_never_touches_evidence_under_dot_claude(tmp_path: Path) -> None:
    # El barrido buscaba `*-notes.es-mx.tex` en todo el árbol y corrigió una
    # copia de evidencia en `.claude/workbench/`: contaba 10 notas en un lote de 9.
    repo, note, runner = setup(tmp_path)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    evidence = repo / ".claude" / "workbench" / "old" / "copy-notes.es-mx.tex"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("title=#1\n", encoding="utf-8")
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({"patron": "p", "senal_del_verificador": "compile:error",
                                  "fix_generico": {"tipo": "mechanical", "buscar": "title=#1", "reemplazar": "title={#1}"},
                                  "archivos_donde_ya_se_aplico": []}) + "\n", encoding="utf-8")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    loop(repo, "sweep", "--bench", str(bench), "--iteration", "1", "--memory", str(memory), cache=tmp_path / "c")
    assert evidence.read_text(encoding="utf-8") == "title=#1\n"
    row = json.loads((bench / "sweep.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["notas_revisadas"] == 1


def write_plan(repo: Path, batch: str, notes: list[Path]) -> Path:
    plan = repo / ".claude/workbench/translation/plan.tsv"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("order\tbatch\tbytes\tnotes\tpaths\n1\t%s\t0\t%d\t%s\n"
                    % (batch, len(notes), " ".join(str(n.relative_to(repo)) for n in notes)), encoding="utf-8")
    return plan


def test_advance_runs_a_clean_batch_in_one_iteration(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    write_plan(repo, "cs000", [note])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", runner=runner, cache=tmp_path / "c")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 1 and rows[0].split("\t")[6] == "0"


def test_advance_retranslates_local_signals_and_stops_bounded(tmp_path: Path) -> None:
    # El runner falso repite el mismo defecto al retraducir: `advance` tiene
    # que parar en su tope de iteraciones y pedir juicio (exit 3), no girar.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El training usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    write_plan(repo, "cs000", [note])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", "--max-iterations", "3",
                  runner=runner, cache=tmp_path / "c")
    assert result.returncode == 3, result.stdout + result.stderr
    assert "juicio" in result.stderr
    # self-evolving-agents-2026: «resolubilidad» e «internalizar» sobrevivieron
    # a tres retraducciones cada una y sólo cedieron a una fila del glosario.
    # Una señal que vuelve igual tras retraducir su fragmento no es local: se
    # detiene tras esa retraducción, no en el tope.
    assert "sobrevive" in result.stderr and "prose:english:training" in result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 2 and int(rows[1].split("\t")[5]) >= 1


def test_advance_keeps_retranslating_a_signal_that_changes(tmp_path: Path) -> None:
    # La gemela: si la retraducción cambia la señal (otra palabra), el fragmento
    # sí responde a retraducir y el lote sigue hasta quedar limpio.
    repo, note, runner = setup(tmp_path)
    changing = FAKE_RUNNER.replace("for n, zh in enumerate(items, 1):",
                                   "state = Path(__file__).with_suffix('.calls')\n"
                                   "calls = int(state.read_text()) if state.exists() else 0\n"
                                   "state.write_text(str(calls + 1))\n"
                                   "table['训练用 checkpoint。'] = ['El training usa checkpoint.', "
                                   "'El throughput usa checkpoint.', 'El entrenamiento usa checkpoint.'][min(calls, 2)]\n"
                                   "for n, zh in enumerate(items, 1):")
    runner.write_text(changing, encoding="utf-8")
    write_plan(repo, "cs000", [note])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", "--max-iterations", "4",
                  runner=runner, cache=tmp_path / "c")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert [r.split("\t")[6] for r in rows] == ["1", "1", "0"]


def test_advance_stops_on_a_shared_cause_without_retranslating(tmp_path: Path) -> None:
    # Ruta 2: la misma señal en dos notas se decide una vez; `advance` no la
    # retraduce nota por nota, se detiene y la nombra.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El training usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    other = repo / "cs000" / "lecture02" / "lecture02-notes.tex"
    other.parent.mkdir(parents=True)
    other.write_text(NOTE, encoding="utf-8")
    write_plan(repo, "cs000", [note, other])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", runner=runner, cache=tmp_path / "c")
    assert result.returncode == 3
    assert "prose:english:training" in result.stderr and "compartida" in result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 1


WAVE = REPO_ROOT / "tools" / "scripts" / "translate_wave.sh"


def test_advance_no_sweep_never_writes_the_memory(tmp_path: Path) -> None:
    # En una ola, varios lotes corren a la vez: un barrido por lote reescribiría
    # la memoria en paralelo y perdería entradas. `--no-sweep` la deja intacta.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El training usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    write_plan(repo, "cs000", [note])
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({"patron": "p", "senal_del_verificador": "prose:english:training",
                                  "fix_generico": {"tipo": "mechanical", "buscar": "training", "reemplazar": "entrenamiento"},
                                  "archivos_donde_ya_se_aplico": ["x"]}) + "\n", encoding="utf-8")
    before = memory.read_bytes()
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", "--memory", str(memory),
                  "--no-sweep", "--max-iterations", "2", runner=runner, cache=tmp_path / "c")
    # Que corrió de verdad: sin esto, un `--no-sweep` desconocido aprobaba sin ejecutar nada.
    assert result.returncode == 3, result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 2
    assert memory.read_bytes() == before
    assert not (repo / ".claude/workbench/translation/cs000/sweep.jsonl").exists()


def test_a_wave_runs_batches_with_gnu_parallel_then_one_sweep_and_triage(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    other = repo / "cs001" / "lecture01" / "lecture01-notes.tex"
    other.parent.mkdir(parents=True)
    other.write_text(NOTE, encoding="utf-8")
    plan = repo / ".claude/workbench/translation/plan.tsv"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("order\tbatch\tbytes\tnotes\tpaths\n"
                    "1\tcs000\t1\t1\tcs000/lecture01/lecture01-notes.tex\n"
                    "2\tcs001\t2\t1\tcs001/lecture01/lecture01-notes.tex\n", encoding="utf-8")
    env = dict(os.environ, TRANSLATION_RUNNER=str(runner), THYROX_CACHE_DIR=str(tmp_path / "c"))
    result = subprocess.run(["bash", str(WAVE), "--from", "1", "--to", "2", "--jobs", "2", "--model", "claude-sonnet-5"],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    wave = next((repo / ".claude/workbench/translation/waves").iterdir())
    joblog = (wave / "joblog.tsv").read_text(encoding="utf-8").splitlines()
    assert len(joblog) == 3 and all(l.split("\t")[6] == "0" for l in joblog[1:])  # columna Exitval
    assert (wave / "sweep.jsonl").is_file() and (wave / "triage.tsv").is_file()
    for batch in ("cs000", "cs001"):
        assert (repo / f".claude/workbench/translation/{batch}/iterations/01/signals.jsonl").is_file()


def test_a_note_one_level_deep_is_its_own_course(tmp_path: Path) -> None:
    # `self-evolving-agents-2026/…-notes.tex` salía como el curso «.» (lote `raiz`).
    repo = tmp_path / "repo"
    note = repo / "solo-course" / "solo-course-notes.tex"
    note.parent.mkdir(parents=True)
    note.write_text("x", encoding="utf-8")
    assert loop(repo, "plan", "--out", "plan.tsv").returncode == 0
    row = (repo / "plan.tsv").read_text(encoding="utf-8").splitlines()[1].split("\t")
    assert row[1] == "solo-course", row


def test_included_chapters_are_translated_and_verified_as_units(tmp_path: Path) -> None:
    # `self-evolving-agents-2026` incluye 9 capítulos con chino; `prepare` solo
    # traducía la nota, y `\IfFileExists{x.tex}` seguía mirando el capítulo zh.
    chapter_zh = "\\section{训练}\n训练用 checkpoint。\n"
    source = NOTE.replace("\\end{document}",
                          "\\IfFileExists{ch01/ch01-chapter.tex}{\\input{ch01/ch01-chapter.tex}}{}\n\\end{document}")
    repo, note, runner = setup(tmp_path, source=source)
    chapter = note.parent / "ch01" / "ch01-chapter.tex"
    chapter.parent.mkdir()
    chapter.write_text(chapter_zh, encoding="utf-8")
    result = loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note),
                  runner=runner, cache=tmp_path / "c")
    es_note = note.with_name("lecture01-notes.es-mx.tex").read_text(encoding="utf-8")
    assert "\\IfFileExists{ch01/ch01-chapter.es-mx.tex}{\\input{ch01/ch01-chapter.es-mx.tex}}{}" in es_note
    es_chapter = chapter.with_name("ch01-chapter.es-mx.tex")
    assert es_chapter.is_file() and "El entrenamiento usa checkpoint." in es_chapter.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    # Un capítulo no compila solo (no tiene `\\documentclass`): lo compila su nota.
    compiled = tmp_path / "k.jsonl"
    loop(repo, "verify", "--compile", "--out", str(compiled), str(es_chapter), cache=tmp_path / "c3")
    assert "compile:" not in compiled.read_text(encoding="utf-8")
    # Un capítulo con chino sin traducir sale en la verificación.
    es_chapter.write_text(chapter_zh, encoding="utf-8")
    out = tmp_path / "s.jsonl"
    loop(repo, "verify", "--out", str(out), str(note.with_name("lecture01-notes.es-mx.tex")), str(es_chapter),
         cache=tmp_path / "c2")
    assert "parity:residual-han" in out.read_text(encoding="utf-8")


def test_translate_allows_the_measured_turn_tail_and_names_the_rejection(tmp_path: Path) -> None:
    # Ola 1: con `Grep` sobre la fuente, 18 de 93 ítems agotaron 4 turnos
    # (`error_max_turns`) y el mensaje solo decía «sin marcadores».
    repo, note, runner = setup(tmp_path)
    runner.write_text(FAKE_RUNNER.replace('result = "SIN MARCADORES" if "OMITIR" in body else',
                                          'result = "" if "OMITIR" in body else'), encoding="utf-8")
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    args = json.loads(runner.with_suffix(".args").read_text())
    assert args[args.index("--max-turns") + 1] == "8"
    # Un ítem sin marcadores nombra su causa si la salida de `claude -p` la trae.
    out = next(bench.glob("translate/*"))
    first = out / "1.json"
    data = json.loads(first.read_text())
    data.update({"result": "", "subtype": "error_max_turns"})
    first.write_text(json.dumps(data))
    mod = load_loop()
    targets = {l.split("\t")[3]: l.split("\t")[4] for l in (bench / "units.tsv").read_text(encoding="utf-8").splitlines()}
    import contextlib, io
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        mod.collect_results(out, targets)
    assert "error_max_turns" in buffer.getvalue()


def test_advance_retries_chunks_that_were_rejected(tmp_path: Path) -> None:
    # Ola 1: un lote que no se ensambló por fragmentos rechazados pedía juicio
    # tras un solo intento; esos fragmentos son la siguiente vuelta, no un juicio.
    repo, note, runner = setup(tmp_path)
    flaky = FAKE_RUNNER.replace("for n, zh in enumerate(items, 1):",
                                "state = Path(__file__).with_suffix('.calls')\n"
                                "calls = int(state.read_text()) if state.exists() else 0\n"
                                "state.write_text(str(calls + 1))\n"
                                "for n, zh in enumerate(items, 1):")
    flaky = flaky.replace('result = "SIN MARCADORES" if "OMITIR" in body else',
                          'result = "" if (calls == 0 and n == 1) else "SIN MARCADORES" if "OMITIR" in body else')
    runner.write_text(flaky, encoding="utf-8")
    write_plan(repo, "cs000", [note])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", runner=runner, cache=tmp_path / "c")
    assert result.returncode == 0, result.stdout + result.stderr
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert [r.split("\t")[6] for r in rows] == ["sin-ensamblar", "0"]


def test_a_mechanical_fix_that_extends_its_own_text_is_idempotent(tmp_path: Path) -> None:
    # Llevar xeCJK a las notas ya traducidas es «…{spanish}» → «…{spanish}\n\usepackage{xeCJK}»:
    # el reemplazo contiene lo buscado y cada ola lo volvería a duplicar.
    repo, note, runner = setup(tmp_path)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    # Ancla propia: el preámbulo localizado ya trae xeCJK con sus comentarios.
    anchor = "\\begin{document}\n"
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({"patron": "p", "senal_del_verificador": "compile:missing-glyph",
                                  "fix_generico": {"tipo": "mechanical", "buscar": anchor,
                                                   "reemplazar": anchor + "% marca-idempotente\n"},
                                  "archivos_donde_ya_se_aplico": []}) + "\n", encoding="utf-8")
    bench = repo / ".claude" / "workbench" / "translation" / "cs000"
    for iteration in ("1", "2"):
        loop(repo, "sweep", "--bench", str(bench), "--iteration", iteration, "--memory", str(memory), cache=tmp_path / "c")
    text = note.with_name("lecture01-notes.es-mx.tex").read_text(encoding="utf-8")
    assert text.count("% marca-idempotente") == 1, text.count("% marca-idempotente")


def write_signals(root: Path, batch: str, rows: list[dict]) -> None:
    here = root / ".claude/workbench/translation" / batch / "iterations" / "01"
    here.mkdir(parents=True, exist_ok=True)
    (here / "signals.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                        encoding="utf-8")


def test_a_generic_signal_is_grouped_by_its_cause_not_by_its_name(tmp_path: Path) -> None:
    # Plan v3: «no todo nombre duplicado es la misma causa». `compile:missing-glyph`
    # con «（» en una nota y «张» en otra son dos causas: el paréntesis de ancho
    # completo (memoria mecánica) y la falta de fuente CJK (xeCJK). En cambio
    # «张» y «李» en dos notas son una sola: ningún Han tiene glifo.
    mod = load_loop()
    glyph = "Missing character: There is no {} (U+{:04X}) in font [lmroman10-regular]:mapping=t"
    write_signals(tmp_path, "a", [
        {"note": "a/n1.es-mx.tex", "signal": "compile:missing-glyph", "detail": glyph.format("（", 0xFF08)},
        {"note": "a/n1.es-mx.tex", "signal": "compile:error",
         "detail": "! Undefined control sequence. | l.40 ...de que \\enquote"}])
    write_signals(tmp_path, "b", [
        {"note": "b/n2.es-mx.tex", "signal": "compile:missing-glyph", "detail": glyph.format("张", 0x5F20)},
        {"note": "b/n2.es-mx.tex", "signal": "compile:error",
         "detail": "! Undefined control sequence. | l.12 el año del \\citep"}])
    write_signals(tmp_path, "c", [
        {"note": "c/n3.es-mx.tex", "signal": "compile:missing-glyph", "detail": glyph.format("李", 0x674E)},
        {"note": "c/n3.es-mx.tex", "signal": "prose:english:pools", "detail": ""}])
    memory = tmp_path / "memory.jsonl"
    memory.write_text("", encoding="utf-8")
    routes = mod.classify(tmp_path, memory)
    assert routes["compile:missing-glyph:han"] == ("shared", ["b/n2.es-mx.tex", "c/n3.es-mx.tex"])
    assert routes["compile:missing-glyph:U+FF08"][0] == "local"
    assert routes["compile:error:Undefined control sequence.:\\enquote"][0] == "local"
    assert routes["compile:error:Undefined control sequence.:\\citep"][0] == "local"
    # Una señal que ya lleva su texto en el nombre no cambia de clave.
    assert routes["prose:english:pools"][0] == "local"


def test_measure_records_the_net_effect_of_each_decision(tmp_path: Path) -> None:
    # Plan v3, paso 3: una causa compartida a la vez, midiendo el efecto neto
    # (señales resueltas menos señales introducidas) antes de la siguiente.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "El throughput usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    es = note.with_name("lecture01-notes.es-mx.tex")
    table = repo / ".claude/workbench/translation/decisions.tsv"
    # Sin medición anterior no hay neto: la primera es la línea base. Comparar
    # contra la última iteración de cada lote mezclaba alcances (una iteración
    # «sin-ensamblar» deja 0 señales; los preámbulos compartidos no están en
    # ninguna) y en self-evolving-agents-2026 dio −6 a una decisión que resolvió 1.
    baseline = loop(repo, "measure", "--decision", "línea base", cache=tmp_path / "c")
    assert baseline.returncode == 0 and "introducida" not in baseline.stderr, baseline.stderr
    header, *rows = table.read_text(encoding="utf-8").splitlines()
    row = dict(zip(header.split("\t"), rows[-1].split("\t")))
    assert (row["before"], row["after"], row["net"]) == ("", "1", ""), row
    # La decisión resuelve «throughput» e introduce «pools» sin querer.
    es.write_text(es.read_text(encoding="utf-8").replace("El throughput usa", "Los pools del rendimiento usan"),
                  encoding="utf-8")
    result = loop(repo, "measure", "--decision", "throughput → rendimiento", cache=tmp_path / "c")
    assert result.returncode == 0, result.stdout + result.stderr
    header, *rows = table.read_text(encoding="utf-8").splitlines()
    row = dict(zip(header.split("\t"), rows[-1].split("\t")))
    assert row["decision"] == "throughput → rendimiento"
    assert (row["resolved"], row["introduced"], row["net"]) == ("1", "1", "0"), row
    assert "prose:english:pools" in result.stderr
    # La siguiente medición se compara contra ésta, no contra la iteración: sin
    # cambios da 0/0/0; contra la iteración daría 1 resuelta y 1 introducida.
    # (La primera versión de esta prueba corregía «pools» aquí y no discriminaba:
    # contra la iteración también daba 1 resuelta y 0 introducidas.)
    loop(repo, "measure", "--decision", "repetición sin cambios", cache=tmp_path / "c")
    row = dict(zip(header.split("\t"), table.read_text(encoding="utf-8").splitlines()[-1].split("\t")))
    assert (row["resolved"], row["introduced"], row["net"], row["after"]) == ("0", "0", "0", "1"), row
    # Un neto negativo detiene: la decisión se revierte antes de la siguiente.
    es.write_text(es.read_text(encoding="utf-8").replace("del rendimiento", "del throughput"), encoding="utf-8")
    result = loop(repo, "measure", "--decision", "rendimiento → throughput", cache=tmp_path / "c")
    assert result.returncode == 4, result.stdout + result.stderr
    assert "se revierte" in result.stderr
    assert len(list((repo / ".claude/workbench/translation/measures").glob("*.jsonl"))) == 4


SESSION_LIMIT = "You've hit your session limit · resets 4am (UTC)"


def test_a_session_limit_stops_the_batch_instead_of_retrying(tmp_path: Path) -> None:
    # Ola 2: 105 de 117 rechazos eran esta respuesta, con `subtype: success` y
    # sin marcadores. `advance` la tomó por un fragmento rechazado y lo reintentó
    # tres veces más en cs146s y en zhang-xiaojun. Contra el límite de la cuenta
    # no hay reintento útil: el lote se detiene con 5 y lo dice.
    repo, note, runner = setup(tmp_path)
    limited = FAKE_RUNNER.replace("for n, zh in enumerate(items, 1):",
                                  "state = Path(__file__).with_suffix('.calls')\n"
                                  "calls = int(state.read_text()) if state.exists() else 0\n"
                                  "state.write_text(str(calls + 1))\n"
                                  "for n, zh in enumerate(items, 1):")
    limited = limited.replace('result = "SIN MARCADORES" if "OMITIR" in body else',
                              f'result = {SESSION_LIMIT!r} if n == 1 else "SIN MARCADORES" if "OMITIR" in body else')
    runner.write_text(limited, encoding="utf-8")
    write_plan(repo, "cs000", [note])
    result = loop(repo, "advance", "--batch", "cs000", "--model", "claude-sonnet-5", runner=runner, cache=tmp_path / "c")
    assert result.returncode == 5, result.stdout + result.stderr
    assert "límite de sesión" in result.stderr
    assert runner.with_suffix(".calls").read_text() == "1"
    rows = (repo / ".claude/workbench/translation/batches.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert [(r.split("\t")[6], r.split("\t")[7]) for r in rows] == [("limite", "5")]


def test_a_wave_stops_launching_batches_once_one_hits_the_session_limit(tmp_path: Path) -> None:
    # Ola 2: los siete lotes siguieron lanzando `claude -p` contra el límite de
    # la cuenta. El primero que lo encuentra deja una marca, y los siguientes
    # no arrancan: salen con 5 sin llamar al modelo.
    repo, note, runner = setup(tmp_path)
    limited = FAKE_RUNNER.replace("for n, zh in enumerate(items, 1):",
                                  "state = Path(__file__).with_suffix('.calls')\n"
                                  "calls = int(state.read_text()) if state.exists() else 0\n"
                                  "state.write_text(str(calls + 1))\n"
                                  "for n, zh in enumerate(items, 1):")
    limited = limited.replace('result = "SIN MARCADORES" if "OMITIR" in body else',
                              f'result = {SESSION_LIMIT!r} if True else')
    runner.write_text(limited, encoding="utf-8")
    rows = ["order\tbatch\tbytes\tnotes\tpaths"]
    for k in range(3):
        course = f"cs00{k}"
        path = repo / course / "lecture01" / "lecture01-notes.tex"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(NOTE, encoding="utf-8")
        rows.append(f"{k + 1}\t{course}\t{k + 1}\t1\t{course}/lecture01/lecture01-notes.tex")
    plan = repo / ".claude/workbench/translation/plan.tsv"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("\n".join(rows) + "\n", encoding="utf-8")
    env = dict(os.environ, TRANSLATION_RUNNER=str(runner), THYROX_CACHE_DIR=str(tmp_path / "c"))
    result = subprocess.run(["bash", str(WAVE), "--from", "1", "--to", "3", "--jobs", "1", "--model", "claude-sonnet-5"],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 5, result.stdout + result.stderr
    assert "límite de sesión" in result.stderr
    assert runner.with_suffix(".calls").read_text() == "1"
    for batch in ("cs001", "cs002"):
        assert not (repo / f".claude/workbench/translation/{batch}/iterations").exists(), batch


def test_a_chunk_that_brings_a_replacement_character_is_rejected_on_arrival() -> None:
    # Ola 3: el modelo partió un carácter multibyte («est��» por «está», «qu��»
    # por «qué») y el fragmento llegó a la nota. Si el original no trae U+FFFD,
    # la traducción no puede traerlo.
    mod = load_loop()
    assert mod.structure_problem("推理。", "Global Search est\ufffd\ufffd centrada.") is not None
    assert mod.structure_problem("推理。", "Global Search está centrada.") is None
    assert mod.structure_problem("原文\ufffd。", "Texto con \ufffd heredado.") is None


def test_residual_han_is_grouped_by_the_han_it_leaves(tmp_path: Path) -> None:
    # Ola 3: `parity:residual-han` en cinco notas contaba como una causa
    # compartida. Dos eran el mismo nombre de programa («Ungrounded 不着边际»);
    # las otras tres, restos locales distintos («推理», «构建模型», …).
    mod = load_loop()
    detail = "{} linea(s); primera: {}"
    write_signals(tmp_path, "a", [
        {"note": "a/n1.es-mx.tex", "signal": "parity:residual-han",
         "detail": detail.format(2, "\\newcommand{\\noteauthors}{Compilado a partir de Ungrounded 不着边际 E")},
        {"note": "a/n2.es-mx.tex", "signal": "parity:residual-han",
         "detail": detail.format(2, "\\newcommand{\\noteauthors}{Elaboradas a partir de Ungrounded 不着边际 y")}])
    write_signals(tmp_path, "b", [
        {"note": "b/n3.es-mx.tex", "signal": "parity:residual-han", "detail": detail.format(1, "\\section{Online vs. Offline 推理}")},
        {"note": "b/n4.es-mx.tex", "signal": "parity:residual-han", "detail": detail.format(4, "# 构建模型")}])
    memory = tmp_path / "memory.jsonl"
    memory.write_text("", encoding="utf-8")
    routes = mod.classify(tmp_path, memory)
    assert routes["parity:residual-han:不着边际"] == ("shared", ["a/n1.es-mx.tex", "a/n2.es-mx.tex"])
    assert routes["parity:residual-han:推理"][0] == "local" and routes["parity:residual-han:构建模型"][0] == "local"


def test_sweep_reaches_every_translated_file_that_measure_verifies(tmp_path: Path) -> None:
    # Ola 3: el barrido del respaldo CJK dejó sin tocar cuatro preámbulos
    # compartidos y dos plantillas: sólo recorría `*-notes.es-mx.tex`, mientras
    # `measure` verifica todo `*.es-mx.tex`. El arreglo cubre lo que se mide.
    repo, note, runner = setup(tmp_path)
    preamble = repo / "cs000" / "cs000-preamble.es-mx.tex"
    preamble.write_text("\\usepackage{xeCJK}\n\\setCJKmainfont{FandolSong-Regular.otf}\n", encoding="utf-8")
    memory = tmp_path / "memory.jsonl"
    memory.write_text(json.dumps({
        "patron": "preámbulo sin respaldo CJK", "senal_del_verificador": "compile:missing-glyph",
        "fix_generico": {"tipo": "mechanical", "buscar": "\\usepackage{xeCJK}\n",
                         "reemplazar": "\\usepackage[AutoFallBack=true]{xeCJK}\n"},
        "archivos_donde_ya_se_aplico": []}, ensure_ascii=False) + "\n", encoding="utf-8")
    bench = tmp_path / "bench"
    bench.mkdir()
    result = loop(repo, "sweep", "--bench", str(bench), "--iteration", "1", "--memory", str(memory),
                  cache=tmp_path / "cache")
    assert result.returncode == 0, result.stderr
    assert "AutoFallBack=true" in preamble.read_text(encoding="utf-8")


def test_a_cause_already_decided_is_retranslated_not_held_as_shared(tmp_path: Path) -> None:
    # Ola 4: «auditabilidad» ya tenía su fila de glosario y seguía deteniendo
    # dos lotes como causa compartida, sin que sus fragmentos se retradujeran
    # nunca. Una forma prohibida o rechazada por el glosario ya está decidida,
    # y un U+FFFD es daño de un fragmento: las tres van a retraducción.
    mod = load_loop()
    glyph = "Missing character: There is no � (U+FFFD) in font [lmroman10-regular]:mapping=t"
    rows = lambda n: [
        {"note": f"{n}.es-mx.tex", "signal": "prose:forbidden:la clave está en", "detail": ""},
        {"note": f"{n}.es-mx.tex", "signal": "prose:invented:auditabilidad", "detail": ""},
        {"note": f"{n}.es-mx.tex", "signal": "compile:missing-glyph", "detail": glyph},
        {"note": f"{n}.es-mx.tex", "signal": "prose:english:pipeline", "detail": ""}]
    write_signals(tmp_path, "a", rows("a/n1"))
    write_signals(tmp_path, "b", rows("b/n2"))
    memory = tmp_path / "memory.jsonl"
    memory.write_text("", encoding="utf-8")
    glossary = tmp_path / "glossary.tsv"
    glossary.write_text("term_en\tdecision\tes_mx\tmeaning\tsource\trejected\n"
                        "auditability\ttranslate\tcapacidad de auditoría\tx\ty\tauditabilidad\n", encoding="utf-8")
    routes = mod.classify(tmp_path, memory, glossary)
    assert routes["prose:forbidden:la clave está en"][0] == "local"
    assert routes["prose:invented:auditabilidad"][0] == "local"
    assert routes["compile:missing-glyph:U+FFFD"][0] == "local"
    # Lo que no tiene decisión sigue siendo compartido: se decide una vez.
    assert routes["prose:english:pipeline"][0] == "shared"


def test_retranslate_leaves_each_chunk_a_correction_naming_what_failed(tmp_path: Path) -> None:
    # Ola 5: «antropomorfización», «la clave está en» y «ortogonalización»
    # volvieron en la retraducción porque el modelo no sabía qué había fallado
    # en ese fragmento: sólo recibía la plantilla general. Cada fragmento
    # devuelto a pendientes lleva su nota, con la forma que el glosario adopta.
    dictionary = dict(DICTIONARY, **{"训练用 checkpoint。": "La auditabilidad usa checkpoint."})
    repo, note, runner = setup(tmp_path, dictionary)
    loop(repo, "cycle", "--batch", "cs000", "--model", "claude-sonnet-5", str(note), runner=runner, cache=tmp_path / "c")
    loop(repo, "retranslate", "--batch", "cs000")
    chunks = repo / ".claude/workbench/translation/cs000/chunks"
    corrections = sorted(chunks.rglob("*.correccion.md"))
    assert len(corrections) == 1, corrections
    text = corrections[0].read_text(encoding="utf-8")
    assert "auditabilidad" in text and "capacidad de auditoría" in text
    assert corrections[0].with_name(corrections[0].name.replace(".correccion.md", ".zh.tex")).is_file()
    # La plantilla le dice al modelo que la lea.
    assert "correccion.md" in (REPO_ROOT / "tools/lang/es-mx/translator_prompt.md").read_text(encoding="utf-8")


def test_usage_records_the_memory_gnu_time_measured_for_each_item(tmp_path: Path) -> None:
    # `headless-pool` deja `<n>.time` con «%M %e %U %S» (THYROX 5f7cda74): la
    # memoria pico en KB, la pared y la CPU de cada `claude -p`. Es la medición
    # que reemplaza el `--memfree 3G` estimado. Un ítem sin `.time` no midió:
    # lleva «-», no un cero que se leería como «no usó memoria».
    repo, note, runner = setup(tmp_path)
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    out = next(bench.glob("translate/*"))
    (out / "1.time").write_text("212680 12.34 3.20 0.80\n", encoding="utf-8")
    result = loop(repo, "usage", "--bench", str(bench))
    totals = dict(kv.split("=") for kv in result.stdout.split())
    assert totals["peak_rss_max_kb"] == "212680" and totals["peak_rss_measured"] == "1"
    rows = [r.split("\t") for r in (bench / "usage.tsv").read_text(encoding="utf-8").splitlines()]
    header, first, second = rows[0], rows[1], rows[2]
    assert dict(zip(header, first))["peak_rss_kb"] == "212680" and dict(zip(header, first))["cpu_s"] == "4.00"
    assert dict(zip(header, second))["peak_rss_kb"] == "-"
