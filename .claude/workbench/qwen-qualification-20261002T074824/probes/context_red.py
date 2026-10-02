"""Rojo: translate declara al pool el contexto de sus ítems."""
from pathlib import Path

TEST = Path("/home/user/ai-course-notes/tests/test_translation_loop.py")
OLD = '''    assert value("--task-class") == "analisis"
    assert "--model" not in args
'''
NEW = '''    assert value("--task-class") == "analisis"
    assert value("--context-tokens") == "32768"
    assert "--model" not in args
'''
text = TEST.read_text(encoding="utf-8")
assert text.count(OLD) == 1
TEST.write_text(text.replace(OLD, NEW), encoding="utf-8")
