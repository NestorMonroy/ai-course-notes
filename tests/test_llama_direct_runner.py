"""La respuesta de un fragmento se nombra por el fragmento, no por su posición."""
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
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


class LoadingServer:
    """Servidor que responde 503 las primeras ``loading`` peticiones, como llama-server al cargar."""

    def __init__(self, loading: int) -> None:
        state = {"left": loading, "calls": 0}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                self.rfile.read(int(self.headers["Content-Length"]))
                state["calls"] += 1
                status = 503 if state["left"] > 0 else 200
                state["left"] -= 1
                body = b'{"ok": true}'
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:
                pass

        self.state = state
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()


class LoadingWaitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.poll = runner.LOADING_POLL_S
        runner.LOADING_POLL_S = 0

    def tearDown(self) -> None:
        runner.LOADING_POLL_S = self.poll

    def test_waits_while_the_model_loads(self) -> None:
        server = LoadingServer(loading=2)
        try:
            self.assertEqual(runner.post(server.url, {}, timeout=5), {"ok": True})
            self.assertEqual(server.state["calls"], 3)
        finally:
            server.close()

    def test_gives_up_after_the_loading_deadline(self) -> None:
        server = LoadingServer(loading=10**6)
        try:
            with self.assertRaises(runner.urllib.error.HTTPError):
                runner.post(server.url, {}, timeout=5, loading_wait_s=0)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
