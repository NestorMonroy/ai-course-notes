"""Rojo: la política del proyecto admite también el Qwen de la biblioteca de Ollama, declarado por su fuente."""
from pathlib import Path

TEST = Path("/home/user/ai-course-notes/tests/test_translation_loop.py")
OLD = '''def test_the_shipped_policy_allows_only_the_official_qwen_without_fallback() -> None:
    policy = json.loads((REPO_ROOT / "tools" / "lang" / "es-mx" / "model-policy.json").read_text(encoding="utf-8"))
    assert policy["fallback"] == {"enabled": False}
    assert policy["allowed"] == [{"runtime": "ollama", "repository": "Qwen/Qwen2.5-7B-Instruct-GGUF", "quantization": "Q4_K_M"}]
'''
NEW = '''def test_the_shipped_policy_allows_only_qwen_without_fallback() -> None:
    policy = json.loads((REPO_ROOT / "tools" / "lang" / "es-mx" / "model-policy.json").read_text(encoding="utf-8"))
    assert policy["fallback"] == {"enabled": False}
    assert policy["allowed"] == [
        {"runtime": "ollama", "repository": "Qwen/Qwen2.5-7B-Instruct-GGUF", "quantization": "Q4_K_M"},
        {"runtime": "ollama", "repository": "library/qwen2.5-7b-instruct", "source": "ollama", "quantization": "Q4_K_M"},
    ]
'''
text = TEST.read_text(encoding="utf-8")
assert text.count(OLD) == 1
TEST.write_text(text.replace(OLD, NEW), encoding="utf-8")
