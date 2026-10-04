"""«correr» → ejecutar en la prosa del proyecto (tools/lang/es-mx/prohibited_forms.txt, sección de coloquialismos)."""
from pathlib import Path

ROOT = Path("/home/user/ai-course-notes")
EDITS = {
    "tools/scripts/translate_wave.sh": [
        ("# El barrido (ruta 1) y el triage (ruta 2) corren una sola vez al final: el",
         "# El barrido (ruta 1) y el triage (ruta 2) se ejecutan una sola vez al final: el"),
        ("así que no puede correr", "así que no puede ejecutarse"),
    ],
    "tests/test_translation_loop.py": [
        ("mientras el pool corre; la", "mientras el pool se ejecuta; la"),
        ("varios lotes corren a la vez: un barrido", "varios lotes se ejecutan a la vez: un barrido"),
        ("# Que corrió de verdad:", "# Que se ejecutó de verdad:"),
    ],
    "tools/scripts/translation_loop.py": [
        ("GNU Parallel mientras corre (`--memfree`", "GNU Parallel mientras se ejecuta (`--memfree`"),
        ("# corrió sin un 429;", "# ejecutó sin un 429;"),
        ("varios lotes corren a la vez: el barrido", "varios lotes se ejecutan a la vez: el barrido"),
        ("así que corre una sola vez al final de la ola.", "así que se ejecuta una sola vez al final de la ola."),
    ],
    "docs/ES_MX_TRANSLATION_PLAN.md": [
        ("mientras el pool corre.**", "mientras el pool se ejecuta.**"),
        ("el piloto corrió sin ningún 429.", "el piloto ejecutó sin ningún 429."),
        ("Sin él el pool corre", "Sin él el pool se ejecuta"),
        ("y el triage (ruta 2) corren **una sola vez**", "y el triage (ruta 2) se ejecutan **una sola vez**"),
        ("el ciclo corrió en modo reactivo", "el ciclo se ejecutó en modo reactivo"),
        ("**La ola corre sola de principio a fin**", "**La ola se ejecuta sola de principio a fin**"),
        ("fragmentos) corrieron a la vez", "fragmentos) se ejecutaron a la vez"),
        ("los lotes grandes corren con `--jobs 2`", "los lotes grandes se ejecutan con `--jobs 2`"),
    ],
}
for rel, pairs in EDITS.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{rel}: {text.count(old)} de {old!r}"
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
print("hecho")
