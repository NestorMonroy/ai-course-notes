"""Verde: translate pasa --context-tokens al pool, y tools/thyrox nombra el archivo de cualificaciones."""
from pathlib import Path

ROOT = Path("/home/user/ai-course-notes")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path.name}: {text.count(old)} coincidencias de {old[:60]!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


loop = ROOT / "tools/scripts/translation_loop.py"
replace_once(loop, '''BEGIN_MARK, END_MARK = "<<<ES", "ES>>>"
''', '''BEGIN_MARK, END_MARK = "<<<ES", "ES>>>"
# El contexto que cada ítem necesita por turno, declarado al pool para que el
# recomendador no exija su piso de subagente (126 029 tokens), que ningún modelo
# local de 32k alcanza. Medido en 400 ítems de olas anteriores: p50 8 906, p90
# 13 406, máximo 20 984 tokens por turno. 32 768 es el máximo de Qwen 2.5 7B, y
# la cualificación de la clase se mide con ese contexto.
CONTEXT_TOKENS = 32768
''')
replace_once(loop, '''           "--task-class", args.task_class, "--model-policy", str(args.model_policy),
''', '''           "--task-class", args.task_class, "--model-policy", str(args.model_policy),
           "--context-tokens", str(CONTEXT_TOKENS),
''')

readme = ROOT / "tools/thyrox/README.md"
replace_once(readme, "   | `THYROX_WORKBENCH_DIR` | `<consumer>/.claude/workbench` |\n",
             "   | `THYROX_WORKBENCH_DIR` | `<consumer>/.claude/workbench` |\n"
             "   | `THYROX_MODEL_QUALIFICATIONS` | `<consumer>/.claude/models/qualifications.json`: las cualificaciones que midió ESTE proyecto, con su suite (`tools/lang/es-mx/qualification/`) |\n")
