"""Una ola que muere antes de que GNU Parallel escriba sus filas queda registrada.

Parallel escribe la fila de un trabajo en ``joblog.tsv`` sólo cuando el trabajo
termina; si el anfitrión se reinicia a mitad, la ola queda con la cabecera sola
y nadie la cuenta como falla (``translate_wave.sh`` lee la columna 7).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))
import wave_interruptions as wi  # noqa: E402

HEADER = "Seq\tHost\tStarttime\tJobRuntime\tSend\tReceive\tExitval\tSignal\tCommand\n"


def make_wave(waves: Path, name: str, batches: list[str], finished: list[str]) -> Path:
    wave = waves / name
    wave.mkdir(parents=True)
    (wave / "batches.txt").write_text("".join(f"{b}\n" for b in batches), encoding="utf-8")
    rows = "".join(f"{i}\t:\t1.0\t2.0\t0\t0\t0\t0\trun_batch {b}\n" for i, b in enumerate(finished, 1))
    (wave / "joblog.tsv").write_text(HEADER + rows, encoding="utf-8")
    for b in batches:
        out = wave / "salida" / "1" / b
        out.mkdir(parents=True)
        (out / "stderr").write_text("ultimo\n", encoding="utf-8")
    return wave


def start_holder(args: list[str], cwd: Path | None = None) -> subprocess.Popen:
    """Un proceso que lleva la ruta en su comando; espera a que ``exec`` lo publique."""
    holder = subprocess.Popen(args, cwd=cwd)
    cmdline = Path(f"/proc/{holder.pid}/cmdline")
    for _ in range(100):
        if cmdline.read_bytes().startswith(args[0].encode()):
            return holder
        time.sleep(0.02)
    raise AssertionError("el proceso no publicó su línea de comando")


def test_dead_wave_without_rows_is_recorded(tmp_path):
    waves = tmp_path / "waves"
    dead = make_wave(waves, "20261008T174842Z", ["kaist-cs492d"], [])
    current = make_wave(waves, "20261009T040100Z", ["kaist-cs492d"], [])
    recorded = wi.record(waves, current, alive=lambda wave: False)
    assert recorded == [(dead.name, "kaist-cs492d")]
    rows = (dead / "interrupted.tsv").read_text(encoding="utf-8").splitlines()
    assert rows[0].split("\t") == list(wi.COLUMNS)
    fields = dict(zip(wi.COLUMNS, rows[1].split("\t")))
    assert fields["batch"] == "kaist-cs492d" and fields["detected_by"] == current.name
    assert fields["last_output_utc"] != "-"
    assert not (current / "interrupted.tsv").exists()  # la ola en curso no se juzga


def test_only_batches_without_row_are_recorded(tmp_path):
    waves = tmp_path / "waves"
    dead = make_wave(waves, "20261008T062318Z", ["a", "b"], ["a"])
    current = make_wave(waves, "20261009T040100Z", ["c"], [])
    assert wi.record(waves, current, alive=lambda wave: False) == [(dead.name, "b")]


def test_finished_wave_is_not_recorded(tmp_path):
    waves = tmp_path / "waves"
    done = make_wave(waves, "20261008T063730Z", ["cs224r"], ["cs224r"])
    current = make_wave(waves, "20261009T040100Z", ["c"], [])
    assert wi.record(waves, current, alive=lambda wave: False) == []
    assert not (done / "interrupted.tsv").exists()


def test_live_wave_is_not_recorded(tmp_path):
    """Dos lazos (llama-direct y el pool) lanzan olas sobre el mismo árbol."""
    waves = tmp_path / "waves"
    live = make_wave(waves, "20261009T030000Z", ["cs25"], [])
    current = make_wave(waves, "20261009T040100Z", ["c"], [])
    assert wi.record(waves, current, alive=lambda wave: wave == live) == []
    assert not (live / "interrupted.tsv").exists()


def test_recorded_once(tmp_path):
    waves = tmp_path / "waves"
    dead = make_wave(waves, "20261008T174842Z", ["kaist-cs492d"], [])
    first = make_wave(waves, "20261009T040100Z", ["c"], ["c"])
    assert wi.record(waves, first, alive=lambda wave: False) == [(dead.name, "kaist-cs492d")]
    second = make_wave(waves, "20261009T050000Z", ["c"], [])
    assert wi.record(waves, second, alive=lambda wave: False) == []
    assert len((dead / "interrupted.tsv").read_text(encoding="utf-8").splitlines()) == 2


def test_process_alive_sees_parallel_cmdline(tmp_path):
    """La vida se mide por un proceso cuyo comando nombra la ola: Parallel lleva
    ``--joblog <ola>/joblog.tsv`` mientras corre algún lote."""
    wave = tmp_path / "waves" / "20261009T040100Z"
    wave.mkdir(parents=True)
    holder = start_holder([sys.executable, "-c", "import time; time.sleep(30)", str(wave / "joblog.tsv")])
    try:
        assert wi.process_alive(wave)
    finally:
        holder.kill()
        holder.wait()
    assert not wi.process_alive(wave)


def test_process_alive_resolves_relative_paths_by_cwd(tmp_path):
    """Una ola homónima en otro árbol no cuenta como viva; una relativa al cwd, sí."""
    wave = tmp_path / "a" / "waves" / "20261009T040100Z"
    twin = tmp_path / "b" / "waves" / "20261009T040100Z"
    wave.mkdir(parents=True)
    twin.mkdir(parents=True)
    holder = start_holder([sys.executable, "-c", "import time; time.sleep(30)", "waves/20261009T040100Z/joblog.tsv"], cwd=tmp_path / "a")
    try:
        assert wi.process_alive(wave)
        assert not wi.process_alive(twin)
    finally:
        holder.kill()
        holder.wait()
