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
    assert rows[0].split("\t") == ["chunk", "han", "letters", "input", "cache_creation", "cache_read", "output"]
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
