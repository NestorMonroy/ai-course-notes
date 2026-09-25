"""Traducción de las cadenas de las figuras conceptuales a `figure_text.tsv`.

Las cadenas se agrupan en lotes, un `claude -p` por lote vía headless-pool; el
modelo devuelve un TSV `zh<TAB>es` entre marcadores y el guion solo acepta
filas cuyo `zh` es exactamente una cadena pedida en ese lote. Un runner falso
cumple el contrato para probar el ciclo sin gastar tokens.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "translate_figure_text.py"

FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
assert args[args.index("--tools") + 1] == "Read"
index = []
for n, item in enumerate([l for l in sys.stdin.read().splitlines() if l.strip()], 1):
    index.append(f"{n}\t{item}")
    strings = Path(item).read_text(encoding="utf-8").splitlines()
    rows = [f"{s}\tES({s})" for s in strings if s != "漏掉"]
    rows.append("不是请求的\tINVENTADA")  # una fila que el lote no pidió
    result = "<<<TSV\n" + "\n".join(rows) + "\nTSV>>>\n"
    (out / f"{n}.json").write_text(json.dumps({"result": result, "usage": {"output_tokens": 5}}))
(out / "index.tsv").write_text("\n".join(index) + "\n")
print("items=%d ok=%d fallidos=0" % (len(index), len(index)))
'''


def setup(tmp_path: Path, strings: list[str]) -> tuple[Path, Path, dict]:
    runner = tmp_path / "fake_run.py"
    runner.write_text(FAKE, encoding="utf-8")
    runner.chmod(0o755)
    missing = tmp_path / "missing.txt"
    missing.write_text("\n".join(strings) + "\n", encoding="utf-8")
    env = {**os.environ, "TRANSLATION_RUNNER": str(runner)}
    return missing, tmp_path / "figure_text.tsv", env


def run(args: list[str], env: dict):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO_ROOT)


def test_batches_are_translated_and_only_requested_rows_are_kept(tmp_path: Path) -> None:
    strings = ["读图：从左到右", "调用工具", "Agent 最小循环", "记忆"]
    missing, table, env = setup(tmp_path, strings)
    result = run(["--missing", str(missing), "--table", str(table), "--bench", str(tmp_path / "bench"),
                  "--batch", "3", "--model", "claude-sonnet-5"], env)
    assert result.returncode == 0, result.stderr
    rows = table.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "zh\tes_mx"
    assert sorted(rows[1:]) == sorted(f"{s}\tES({s})" for s in strings)
    assert "INVENTADA" not in table.read_text(encoding="utf-8")
    assert len((tmp_path / "bench").glob("translate/*/index.tsv").__next__().read_text().splitlines()) == 2


def test_a_string_the_model_skipped_is_reported_and_the_rest_is_kept(tmp_path: Path) -> None:
    missing, table, env = setup(tmp_path, ["调用工具", "漏掉"])
    table.write_text("zh\tes_mx\n旧的\tanterior\n", encoding="utf-8")
    result = run(["--missing", str(missing), "--table", str(table), "--bench", str(tmp_path / "bench"),
                  "--model", "claude-sonnet-5"], env)
    assert result.returncode == 1
    assert "漏掉" in result.stderr
    rows = table.read_text(encoding="utf-8").splitlines()
    assert "旧的\tanterior" in rows and "调用工具\tES(调用工具)" in rows
    assert not any(r.startswith("漏掉") for r in rows)


def test_a_leading_line_number_column_is_tolerated_but_the_original_must_match(tmp_path: Path) -> None:
    # Medido en la primera corrida: un lote volvió como `16<TAB>能力风险<TAB>…`.
    mod_rows = "1\t调用工具\tLlamar herramientas\n2\t记 忆\tMemoria\n"
    parsed = load().parse_result("<<<TSV\n" + mod_rows + "TSV>>>\n", {"调用工具", "记忆"})
    assert parsed == {"调用工具": "Llamar herramientas"}  # `记 忆` no es la cadena pedida


def test_verify_reports_english_the_row_introduced(tmp_path: Path) -> None:
    table = tmp_path / "figure_text.tsv"
    table.write_text("zh\tes_mx\n"
                     "Agent 最小循环\tEl ciclo mínimo del Agent\n"
                     "训练数据\tLos training data\n"
                     "吞吐量\tEl throughput\n", encoding="utf-8")
    result = run(["--verify", "--table", str(table)], dict(os.environ))
    assert result.returncode == 1
    assert "吞吐量" in result.stdout and "throughput" in result.stdout
    assert "训练数据" in result.stdout and "training" in result.stdout
    # `Agent` ya está en el original: no la introdujo la traducción.
    assert "Agent 最小循环" not in result.stdout


def load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("translate_figure_text", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(mod)
    return mod
