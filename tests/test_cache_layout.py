"""Los archivos de `.claude/cache/` siguen la forma de `thyrox/.claude/build-logs/`.

Cada archivo vive en `.claude/cache/<nombre>/<raíz>-<AAAAMMDDTHHMMSSZ>.<ext>`:
un directorio por trabajo y la marca de tiempo UTC en el nombre, para que una
segunda ejecución no sobrescriba la primera. Se escribían planos y sin fecha
(`ola-1.log`, `fix.log`). La excepción es `translation/`, el almacén de
veredictos del verificador, cuyos nombres son el hash de su contenido.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE = REPO_ROOT / ".claude" / "cache"
NAME = re.compile(r"^.+-\d{8}T\d{6}Z(\.[\w.-]+)?$")
STORES = {"translation"}


def offenders(root: Path) -> list[str]:
    bad = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if parts[0] in STORES:
            continue
        if len(parts) < 2 or not NAME.match(path.name):
            bad.append(str(path.relative_to(root)))
    return bad


def test_every_cache_file_lives_in_its_job_directory_with_an_iso_timestamp() -> None:
    assert offenders(CACHE) == []


def test_the_layout_check_rejects_a_flat_undated_file(tmp_path: Path) -> None:
    (tmp_path / "ola").mkdir()
    (tmp_path / "ola" / "ola-1-20260925T181641Z.log").write_text("x")
    (tmp_path / "translation").mkdir()
    (tmp_path / "translation" / "abc123.json").write_text("{}")
    assert offenders(tmp_path) == []
    (tmp_path / "ola-1.log").write_text("x")
    (tmp_path / "ola" / "sin-fecha.log").write_text("x")
    assert set(offenders(tmp_path)) == {"ola-1.log", "ola/sin-fecha.log"}
