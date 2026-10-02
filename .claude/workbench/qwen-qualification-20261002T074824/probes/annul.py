"""Anula cada guarda de qualification_suite.py y registra qué pruebas caen."""
import subprocess
from pathlib import Path

ROOT = Path("/home/user/ai-course-notes")
SCRIPT = ROOT / "tools/scripts/qualification_suite.py"
OUT = Path(__file__).resolve().parent.parent / "outputs"
ANNULMENTS = {
    "han-excluded": ('        checks.append({"kind": "excludes-pattern", "pattern": HAN_PATTERN})\n', "        pass\n"),
    "reference-kept-structure": ("for token in structure_tokens(zh) if token in reference]", "for token in structure_tokens(zh)]"),
    "comments-are-not-structure": ('    visible = COMMENT_LINE.sub("", text)\n', "    visible = text\n"),
    "initial-case": ('    return f"{escaped[:first]}[{letter.upper()}{letter.lower()}]{escaped[first + 1:]}"\n', "    return escaped\n"),
    "javascript-escape": ('f"\\\\{char}" if char in REGEX_SYNTAX else char', 'f"\\\\{char}" if not char.isalnum() else char'),
    "usable-needs-reference": ("    return reference_of(zh_path).is_file() and ", "    return "),
}
for name, (old, new) in ANNULMENTS.items():
    original = SCRIPT.read_text(encoding="utf-8")
    assert original.count(old) == 1, f"{name}: {original.count(old)}"
    SCRIPT.write_text(original.replace(old, new), encoding="utf-8")
    try:
        run = subprocess.run(["uv", "run", "--quiet", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_qualification_suite.py"],
                             cwd=ROOT, capture_output=True, text=True)
    finally:
        SCRIPT.write_text(original, encoding="utf-8")
    (OUT / f"annul-{name}.txt").write_text(run.stdout + run.stderr, encoding="utf-8")
    failed = [line.split("::")[-1].split(" ")[0] for line in run.stdout.splitlines() if line.startswith("FAILED")]
    print(f"{name}: {len(failed)} caen {failed}")
