"""Los gates del ciclo de traducción (sección 6 del plan).

Un paso que se puede saltar, eventualmente se salta. Escribir la memoria y
barrer el corpus con ella no son pasos de una secuencia: son gates que salen 2
y detienen el ciclo.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "translation_gate.py"

ENTRY = {
    "patron": "el traductor traduce checkpoint",
    "senal_del_verificador": "parity:keep-term:checkpoint",
    "fix_generico": {"tipo": "prompt", "regla": "checkpoint se queda en ingles"},
    "archivos_donde_ya_se_aplico": ["cs329a/lecture01/lecture01-notes.es-mx.tex"],
}


def jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def gate(*args: str):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def signals(tmp_path: Path, *keys: str) -> Path:
    return jsonl(tmp_path / "signals.jsonl", [{"note": "a.es-mx.tex", "signal": k, "detail": ""} for k in keys])


# --- GATE A ---------------------------------------------------------------

def test_gate_a_refuses_an_entry_missing_a_field(tmp_path: Path) -> None:
    broken = {k: v for k, v in ENTRY.items() if k != "fix_generico"}
    memory = jsonl(tmp_path / "memory.jsonl", [broken])
    result = gate("memory", "--memory", str(memory), "--signals", str(signals(tmp_path)))
    assert result.returncode == 2
    assert "GATE A" in result.stderr and "fix_generico" in result.stderr


def test_gate_a_refuses_a_new_signal_without_a_pattern(tmp_path: Path) -> None:
    memory = jsonl(tmp_path / "memory.jsonl", [ENTRY])
    result = gate("memory", "--memory", str(memory),
                  "--signals", str(signals(tmp_path, "parity:keep-term:checkpoint", "parity:formulas")))
    assert result.returncode == 2
    assert "parity:formulas" in result.stderr
    assert "parity:keep-term:checkpoint" not in result.stderr


def test_gate_a_accepts_signals_covered_by_valid_entries(tmp_path: Path) -> None:
    wildcard = dict(ENTRY, senal_del_verificador="prose:english:*")
    memory = jsonl(tmp_path / "memory.jsonl", [ENTRY, wildcard])
    result = gate("memory", "--memory", str(memory),
                  "--signals", str(signals(tmp_path, "parity:keep-term:checkpoint", "prose:english:weights")))
    assert result.returncode == 0, result.stderr


def test_gate_a_refuses_an_unknown_fix_type(tmp_path: Path) -> None:
    odd = dict(ENTRY, fix_generico={"tipo": "magia"})
    memory = jsonl(tmp_path / "memory.jsonl", [odd])
    result = gate("memory", "--memory", str(memory), "--signals", str(signals(tmp_path)))
    assert result.returncode == 2 and "magia" in result.stderr


# --- GATE B ---------------------------------------------------------------

def test_gate_b_refuses_a_sweep_that_skips_a_pattern(tmp_path: Path) -> None:
    second = dict(ENTRY, senal_del_verificador="parity:formulas", patron="se pierde una formula")
    memory = jsonl(tmp_path / "memory.jsonl", [ENTRY, second])
    sweep = jsonl(tmp_path / "sweep.jsonl", [
        {"iteration": 3, "senal_del_verificador": "parity:keep-term:checkpoint", "notas_revisadas": 9, "instancias": 2},
    ])
    result = gate("sweep", "--memory", str(memory), "--sweep-log", str(sweep), "--iteration", "3")
    assert result.returncode == 2
    assert "GATE B" in result.stderr and "parity:formulas" in result.stderr


def test_gate_b_accepts_a_sweep_covering_every_pattern(tmp_path: Path) -> None:
    memory = jsonl(tmp_path / "memory.jsonl", [ENTRY])
    sweep = jsonl(tmp_path / "sweep.jsonl", [
        {"iteration": 2, "senal_del_verificador": "parity:keep-term:checkpoint", "notas_revisadas": 9, "instancias": 0},
    ])
    assert gate("sweep", "--memory", str(memory), "--sweep-log", str(sweep), "--iteration", "2").returncode == 0
    # Un barrido de OTRA iteración no cuenta para esta.
    assert gate("sweep", "--memory", str(memory), "--sweep-log", str(sweep), "--iteration", "3").returncode == 2


def test_gate_b_with_empty_memory_has_nothing_to_sweep(tmp_path: Path) -> None:
    memory = jsonl(tmp_path / "memory.jsonl", [])
    sweep = jsonl(tmp_path / "sweep.jsonl", [])
    assert gate("sweep", "--memory", str(memory), "--sweep-log", str(sweep), "--iteration", "1").returncode == 0


# --- GATE C ---------------------------------------------------------------

def test_gate_c_refuses_a_batch_with_open_signals(tmp_path: Path) -> None:
    review = jsonl(tmp_path / "review.jsonl", [{"note": "a.es-mx.tex", "pages": [1, 2], "verdict": "ok"}])
    result = gate("batch", "--signals", str(signals(tmp_path, "parity:formulas")), "--review-log", str(review))
    assert result.returncode == 2 and "GATE C" in result.stderr


def test_gate_c_refuses_a_batch_without_visual_review(tmp_path: Path) -> None:
    review = jsonl(tmp_path / "review.jsonl", [])
    result = gate("batch", "--signals", str(signals(tmp_path)), "--review-log", str(review))
    assert result.returncode == 2 and "revision visual" in result.stderr


def test_gate_c_closes_a_clean_reviewed_batch(tmp_path: Path) -> None:
    review = jsonl(tmp_path / "review.jsonl", [{"note": "a.es-mx.tex", "pages": [1], "verdict": "ok"}])
    assert gate("batch", "--signals", str(signals(tmp_path)), "--review-log", str(review)).returncode == 0


# --- report ---------------------------------------------------------------

def test_report_flags_a_reactive_loop(tmp_path: Path) -> None:
    """Tantas iteraciones como notas con señal: el ciclo corrió una nota a la vez."""
    log = jsonl(tmp_path / "iterations.jsonl", [
        {"iteration": i, "notes_with_signals": 1, "memory_entries_written": 0, "sweep_notes": 1} for i in range(1, 9)
    ])
    result = gate("report", "--iteration-log", str(log))
    assert "REACTIVO" in result.stdout


def test_report_accepts_a_proactive_loop(tmp_path: Path) -> None:
    log = jsonl(tmp_path / "iterations.jsonl", [
        {"iteration": 1, "notes_with_signals": 8, "memory_entries_written": 2, "sweep_notes": 9},
        {"iteration": 2, "notes_with_signals": 0, "memory_entries_written": 0, "sweep_notes": 9},
    ])
    result = gate("report", "--iteration-log", str(log))
    assert result.returncode == 0 and "REACTIVO" not in result.stdout
