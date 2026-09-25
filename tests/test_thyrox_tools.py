"""Pruebas de los wrappers de tools/thyrox/: ai-course-notes como CONSUMER de THYROX.

Cada prueba copia tools/thyrox/ a un consumer temporal, porque los wrappers
derivan la raiz del consumer de su propia ubicacion. Asi ninguna prueba escribe
en el repositorio real ni en el store de THYROX.
"""
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools" / "thyrox"
THYROX_ROOT = Path(os.environ.get("THYROX_ROOT", REPO_ROOT.parent / "thyrox"))
PROVIDER_STORE = THYROX_ROOT / "agent-results" / "agent_store.sqlite3"

requires_thyrox = pytest.mark.skipif(
    not (THYROX_ROOT / "src" / "paths" / "reach.py").is_file(),
    reason="THYROX no esta disponible junto a este consumer",
)


def make_consumer(tmp_path: Path, env_lines: list[str] | None) -> Path:
    """Un consumer minimo: git init, tools/thyrox/ copiado y un .env opcional."""
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "es-mx"], cwd=consumer, check=True)
    shutil.copytree(TOOLS_DIR, consumer / "tools" / "thyrox")
    if env_lines is not None:
        (consumer / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    return consumer


def clean_env() -> dict[str, str]:
    """El entorno del proceso sin ninguna clave THYROX_* ni VOCAB_GATE_*."""
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("THYROX_", "VOCAB_GATE_", "GIT_"))
    }


def run_tool(consumer: Path, *args: str,
             extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(consumer / "tools" / "thyrox" / args[0]), *args[1:]],
        cwd=consumer, env={**clean_env(), **(extra_env or {})},
        capture_output=True, text=True, timeout=300,
    )


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


@requires_thyrox
def test_run_refuses_without_consumer_env_file(tmp_path: Path) -> None:
    """THYROX_ROOT exportada no basta: sin el .env del consumer, THYROX usaria sus hogares."""
    consumer = make_consumer(tmp_path, env_lines=None)
    result = run_tool(consumer, "run", "--print-env",
                      extra_env={"THYROX_ROOT": str(THYROX_ROOT)})
    assert result.returncode == 2
    assert f"no existe {consumer}/.env" in result.stderr


def test_run_refuses_without_thyrox_root(tmp_path: Path) -> None:
    consumer = make_consumer(tmp_path, env_lines=["THYROX_AGENT_STORE=/x"])
    result = run_tool(consumer, "run", "--print-env")
    assert result.returncode == 2
    assert "THYROX_ROOT" in result.stderr


@requires_thyrox
def test_print_env_exports_consumer_env_file(tmp_path: Path) -> None:
    consumer = make_consumer(tmp_path, env_lines=[f"THYROX_ROOT={THYROX_ROOT}"])
    result = run_tool(consumer, "run", "--print-env")
    assert result.returncode == 0, result.stderr
    assert f"THYROX_ENV_FILE={consumer}/.env" in result.stdout
    assert f"VOCAB_GATE_ROOT={consumer}" in result.stdout


STORE_COMMANDS = ("agent_store", "task_ids", "hallazgo_ids")


@requires_thyrox
@pytest.mark.parametrize("command", STORE_COMMANDS)
def test_store_commands_refused_without_consumer_store(tmp_path: Path, command: str) -> None:
    """Sin store declarado, estos comandos caerian al store de THYROX (H-THYROX-178)."""
    consumer = make_consumer(tmp_path, env_lines=[f"THYROX_ROOT={THYROX_ROOT}"])
    before = digest(PROVIDER_STORE)
    result = run_tool(consumer, "run", command, "--help")
    assert result.returncode == 2
    assert "THYROX_AGENT_STORE" in result.stderr
    assert digest(PROVIDER_STORE) == before


@requires_thyrox
def test_store_command_allowed_when_consumer_declares_store(tmp_path: Path) -> None:
    """Con store declarado, el store resulta el del consumer y no el de THYROX."""
    consumer_store = tmp_path / "consumer" / "agent-results" / "agent_store.sqlite3"
    consumer = make_consumer(tmp_path, env_lines=[
        f"THYROX_ROOT={THYROX_ROOT}",
        f"THYROX_AGENT_STORE={consumer_store}",
    ])
    before = digest(PROVIDER_STORE)
    result = run_tool(consumer, "run", "agent_store", "init")
    assert result.returncode == 0, result.stderr
    assert consumer_store.is_file()
    assert digest(PROVIDER_STORE) == before


@requires_thyrox
def test_prose_vocabulary_reports_invented_and_forbidden(tmp_path: Path) -> None:
    consumer = make_consumer(tmp_path, env_lines=[f"THYROX_ROOT={THYROX_ROOT}"])
    sample = consumer / "sample-notes.tex"
    sample.write_text("La democión del modelo es la regla de oro.\n", encoding="utf-8")
    result = run_tool(consumer, "check-prose-vocabulary", "sample-notes.tex")
    assert result.returncode == 1, result.stderr
    assert "democión" in result.stdout
    assert "regla de oro" in result.stdout


@requires_thyrox
def test_prose_vocabulary_derives_scope_from_git(tmp_path: Path) -> None:
    """Sin argumentos, el alcance son los .tex nuevos o modificados contra la base."""
    consumer = make_consumer(tmp_path, env_lines=[f"THYROX_ROOT={THYROX_ROOT}"])
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    (consumer / "old-notes.tex").write_text("La democión antigua.\n", encoding="utf-8")
    subprocess.run([*git, "add", "-A"], cwd=consumer, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=consumer, check=True)
    subprocess.run(["git", "checkout", "-qb", "feature/x"], cwd=consumer, check=True)

    empty = run_tool(consumer, "check-prose-vocabulary")
    assert empty.returncode == 0, empty.stderr
    assert "0 archivo(s)" in empty.stdout

    (consumer / "new-notes.tex").write_text("Una chamba nueva.\n", encoding="utf-8")
    scoped = run_tool(consumer, "check-prose-vocabulary")
    assert scoped.returncode == 1, scoped.stderr
    assert "chamba" in scoped.stdout
    assert "democión" not in scoped.stdout
