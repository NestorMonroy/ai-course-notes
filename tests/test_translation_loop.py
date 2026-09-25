"""El motor del ciclo de traduccion: preparar, traducir, ensamblar, verificar
y barrer (`docs/ES_MX_TRANSLATION_PLAN.md`, seccion 6).

El traductor real es `headless-pool` de THYROX (un `claude -p` por fragmento).
Aqui lo sustituye un runner falso que hace el mismo contrato de forma
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

# Traduccion que el runner falso aplica por linea. Un fragmento sin entrada
# aqui se deja con su chino, para ejercitar las senales.
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
# `<fragmento zh>\t<fragmento es>`; escribe la traduccion por diccionario.
import json, sys
from pathlib import Path
args = sys.argv[1:]
assert args[0] == "headless-pool", args
out = Path(args[args.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
assert "Write" in args[args.index("--tools") + 1]
table = json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf-8"))
items = [l for l in sys.stdin.read().splitlines() if l.strip()]
for n, item in enumerate(items, 1):
    zh, es = item.split("\t")
    lines = [table.get(l, l) for l in Path(zh).read_text(encoding="utf-8").splitlines()]
    Path(es).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / f"{n}.json").write_text(json.dumps({"is_error": False, "usage": {"input_tokens": 10, "output_tokens": 20}}))
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
    assert len(units) == 3, units  # portada vacia + 2 secciones
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
    # original y no de la traduccion. Perder el caption del listado, en cambio,
    # lo rompe la traduccion y tiene que salir.
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
    assert "0 fragmento(s) por traducir" in again.stdout, again.stdout


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


def test_auto_width_is_derived_from_memory_load_and_cores() -> None:
    mod = load_loop()
    # La medicion del ejecutor: 13 528 MB disponibles, carga 0.86 en 4 nucleos,
    # 26 `claude -p` con 3017 MB de RSS (116 MB cada uno).
    assert mod.auto_width(mem_available_mb=13528, load1=0.86, cpus=4) == 12
    # La memoria acota cuando escasea: 2048 de reserva + 3 procesos de 116 MB.
    assert mod.auto_width(mem_available_mb=2048 + 3 * 116, load1=0.0, cpus=4) == 3
    # Con los nucleos saturados, la cota por CPU baja a su piso.
    assert mod.auto_width(mem_available_mb=13528, load1=8.0, cpus=4) == 1
    assert mod.auto_width(mem_available_mb=100, load1=0.0, cpus=4) == 1


def test_translate_passes_the_derived_width_and_records_the_measurement(tmp_path: Path) -> None:
    repo, note, runner = setup(tmp_path)
    runner.write_text(FAKE_RUNNER.replace(
        'print(f"items=',
        'Path(__file__).with_suffix(".width").write_text(args[args.index("--width") + 1])\nprint(f"items='),
        encoding="utf-8")
    bench = tmp_path / "bench"
    loop(repo, "prepare", "--bench", str(bench), str(note))
    result = loop(repo, "translate", "--bench", str(bench), "--model", "claude-sonnet-5", runner=runner)
    assert result.returncode == 0, result.stderr
    width = int(runner.with_suffix(".width").read_text())
    assert width >= 1
    assert f"width={width}" in result.stderr and "mem_available_mb=" in result.stderr
    other = tmp_path / "bench2"
    loop(repo, "prepare", "--bench", str(other), str(note))
    fixed = loop(repo, "translate", "--bench", str(other), "--model", "claude-sonnet-5", "--width", "2", runner=runner)
    assert runner.with_suffix(".width").read_text() == "2", fixed.stderr
