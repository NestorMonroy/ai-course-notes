"""La respuesta de un fragmento se nombra por el fragmento, no por su posición."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "scripts"))
import llama_direct_runner as runner  # noqa: E402
import translation_loop as loop  # noqa: E402


class ResponseNameTest(unittest.TestCase):
    def test_names_note_and_fragment(self) -> None:
        zh = Path("/x/chunks/cs25-v6__lecture02__lecture02-notes/004.zh.tex")
        self.assertEqual(runner.response_name(zh), "cs25-v6__lecture02__lecture02-notes__004.response")

    def test_same_fragment_number_in_two_notes_does_not_collide(self) -> None:
        a = Path("/x/chunks/note-a/004.zh.tex")
        b = Path("/x/chunks/note-b/004.zh.tex")
        self.assertNotEqual(runner.response_name(a), runner.response_name(b))

    def test_collect_results_reads_the_named_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zh = root / "chunks" / "note-a" / "001.zh.tex"
            zh.parent.mkdir(parents=True)
            zh.write_text("你好\n", encoding="utf-8")
            out = root / "translate" / "run"
            out.mkdir(parents=True)
            key = runner.response_name(zh)
            (out / "index.tsv").write_text(f"{key}\t{zh}\n", encoding="utf-8")
            (out / f"{key}.json").write_text(json.dumps({"result": "<<<ES\nHola\nES>>>"}), encoding="utf-8")
            target = root / "es" / "001.es.tex"
            target.parent.mkdir()
            missing = loop.collect_results(out, {str(zh): str(target)})
            self.assertEqual(missing, [])
            self.assertEqual(target.read_text(encoding="utf-8").strip(), "Hola")


if __name__ == "__main__":
    unittest.main()
