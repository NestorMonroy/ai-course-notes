"""Cadena de herramientas del consumer: `tools/lib/toolchain.sh` y `tools/setup.sh`.

Adaptado de THYROX (`src/lib/toolchain.sh`, `src/lib/logging.sh`) para que
ai-course-notes no dependa del proveedor para instalar lo que usa. Se conservan
sus tres invariantes: la instalación es opt-in, el éxito se prueba volviendo a
buscar el binario (no leyendo el exit del instalador) y cada herramienta se
sondea por su conducta, no por su nombre.
"""
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "tools" / "lib" / "toolchain.sh"
SETUP = REPO_ROOT / "tools" / "setup.sh"


def bash(script: str, path_dirs: list[Path], env: dict | None = None):
    full = {"PATH": ":".join(str(d) for d in path_dirs) + ":/usr/bin:/bin", "HOME": os.environ.get("HOME", "/root")}
    full.update(env or {})
    return subprocess.run(["bash", "-c", f"source '{LIB}'; {script}"], capture_output=True, text=True, env=full)


def fake(bin_dir: Path, name: str, body: str) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text("#!/bin/bash\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_missing_tool_without_opt_in_refuses_by_name(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = bash("notes_toolchain_require_parallel", [empty],
                  {"NOTES_TOOLCHAIN_PARALLEL_BIN": "parallel-que-no-existe"})
    assert result.returncode == 2
    assert "NOTES_INSTALL_PARALLEL=1" in result.stderr


def test_an_installer_that_lies_is_not_believed(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = bash("notes_toolchain_require_parallel", [empty],
                  {"NOTES_TOOLCHAIN_PARALLEL_BIN": "parallel-que-no-existe", "NOTES_INSTALL_PARALLEL": "1",
                   "NOTES_TOOLCHAIN_PARALLEL_INSTALL_CMD": "true"})
    assert result.returncode == 2
    assert "sigue sin resolver" in result.stderr


def test_moreutils_parallel_is_rejected_and_gnu_parallel_is_accepted(tmp_path: Path) -> None:
    other = fake(tmp_path / "moreutils", "parallel", 'echo "parallel [OPTIONS] command -- arguments"')
    assert bash("notes_toolchain_require_parallel", [other.parent]).returncode == 2
    gnu = fake(tmp_path / "gnu", "parallel", 'echo "GNU parallel 20240222"')
    home = tmp_path / "parallel-home"
    result = bash("notes_toolchain_require_parallel", [gnu.parent], {"PARALLEL_HOME": str(home)})
    assert result.returncode == 0, result.stderr
    assert (home / "will-cite").is_file()


def test_a_dictionary_that_accepts_everything_fails_the_probe(tmp_path: Path) -> None:
    # `hunspell -l` lista lo que rechaza; uno que no lista nada acepta `espanol`.
    lax = fake(tmp_path / "lax", "hunspell", "cat >/dev/null")
    result = bash("notes_toolchain_require_hunspell", [lax.parent])
    assert result.returncode == 2 and "espanol" in result.stderr


def test_the_real_es_mx_dictionary_passes_the_probe() -> None:
    result = bash("notes_toolchain_require_hunspell", [])
    assert result.returncode == 0, result.stderr


def test_logging_marks_status_with_brackets_and_no_color_off_a_tty(tmp_path: Path) -> None:
    result = bash("log_success listo; log_warn cuidado; log_error fallo", [])
    assert "[OK]  listo" in result.stdout
    assert "[!!]  cuidado" in result.stderr and "[EE]  fallo" in result.stderr
    assert "\033[" not in result.stdout + result.stderr


def test_setup_uses_no_emoji() -> None:
    text = SETUP.read_text(encoding="utf-8")
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")
    assert not emoji.search(text), emoji.findall(text)
    assert "log_success" in text and "notes_toolchain_require_hunspell" in text


def test_check_mode_writes_nothing_outside_the_repository(tmp_path: Path) -> None:
    # Una corrida para comprobar no instala skills: en la sesión que lo destapó,
    # `setup.sh` sin opciones copió cuatro skills a ~/.claude/skills.
    skills = tmp_path / "skills"
    result = subprocess.run(["bash", str(SETUP), "--check"], capture_output=True, text=True,
                            env={**os.environ, "SKILLS_DIR": str(skills)})
    assert not skills.exists(), result.stdout
    assert "[..]" in result.stdout and "--check" in result.stdout
