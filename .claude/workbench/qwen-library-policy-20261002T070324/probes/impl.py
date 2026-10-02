"""Verde: añade la entrada de la biblioteca de Ollama a la política y lo dice en el módulo."""
import json
from pathlib import Path

ROOT = Path("/home/user/ai-course-notes")
POLICY = ROOT / "tools/lang/es-mx/model-policy.json"
LOOP = ROOT / "tools/scripts/translation_loop.py"

policy = json.loads(POLICY.read_text(encoding="utf-8"))
policy["allowed"].append({"runtime": "ollama", "repository": "library/qwen2.5-7b-instruct",
                          "source": "ollama", "quantization": "Q4_K_M"})
POLICY.write_text(json.dumps(policy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

OLD = """(`tools/lang/es-mx/model-policy.json`: sólo el Qwen oficial, sin respaldo al
proveedor)."""
NEW = """(`tools/lang/es-mx/model-policy.json`: sólo Qwen 2.5 7B Q4_K_M, sin respaldo al
proveedor; el oficial de Hugging Face o el de la biblioteca de Ollama, éste con
su equivalencia al oficial sin verificar, H-THYROX-312)."""
text = LOOP.read_text(encoding="utf-8")
assert text.count(OLD) == 1
LOOP.write_text(text.replace(OLD, NEW), encoding="utf-8")
