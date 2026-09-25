"""El diccionario es_MX se construye desde las fuentes de RLA-ES.

`tools/lang/build_hunspell_dictionary.sh` reproduce los pasos de
`herramientas/make_dict.sh` de RLA-ES para una localización (afijos sin
comentarios; lista de palabras única y ordenada, con su conteo en la primera
línea), sin las preguntas de publicación que ese guion hace a mano.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD = REPO_ROOT / "tools" / "lang" / "build_hunspell_dictionary.sh"
BUILT = REPO_ROOT / "tools" / "lang" / "es-mx" / "hunspell"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fake_rla(root: Path) -> Path:
    write(root / "ortografia/afijos/afijos.txt", "# general\nSET UTF-8\n")
    write(root / "ortografia/afijos/l10n/es_MX/afijos.txt", "# México\nSET UTF-8\nTRY aeiouñ  # prueba\n")
    write(root / "ortografia/palabras/RAE/Nombres.txt", "# RAE\nseñal/S\ncanción/S\n\n")
    write(root / "ortografia/palabras/RAE/l10n/es_MX/Mexicanismos.txt", "chamba/S\n")
    write(root / "ortografia/palabras/RAE/l10n/es_AR/Argentinismos.txt", "laburo/S\n")
    write(root / "ortografia/palabras/noRAE/Nombres.txt", "señal/S\t# repetida\n")
    write(root / "ortografia/palabras/toponimos/toponimos-comunes.txt", "Oaxaca\n")
    return root


def test_the_build_joins_the_locale_lists_and_counts_them(tmp_path: Path) -> None:
    rla = fake_rla(tmp_path / "rla")
    out = tmp_path / "out"
    result = subprocess.run(["bash", str(BUILD), str(rla), "es_MX", str(out)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lines = (out / "es_MX.dic").read_text(encoding="utf-8").splitlines()
    assert lines[0] == str(len(lines) - 1)
    assert lines[1:] == sorted(set(lines[1:]))
    assert {"señal/S", "canción/S", "chamba/S", "Oaxaca"} <= set(lines[1:])
    assert "laburo/S" not in lines  # otra localización
    assert (out / "es_MX.aff").read_text(encoding="utf-8") == "SET UTF-8\nTRY aeiouñ\n"


def test_a_missing_source_refuses_without_writing(tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = subprocess.run(["bash", str(BUILD), str(tmp_path / "no-existe"), "es_MX", str(out)],
                            capture_output=True, text=True)
    assert result.returncode == 2 and "RLA-ES" in result.stderr
    assert not out.exists()


def test_the_versioned_dictionary_separates_accents_and_enie() -> None:
    words = "español\nespanol\ntraducción\ntraduccion\nseñal\nsenal\ncompare\nexternalizar\n"
    result = subprocess.run(["hunspell", "-i", "utf-8", "-d", str(BUILT / "es_MX"), "-l"],
                            input=words, capture_output=True, text=True,
                            env={"LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"})
    assert result.stdout.split() == ["espanol", "traduccion", "senal"]
