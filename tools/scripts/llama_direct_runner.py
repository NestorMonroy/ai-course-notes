#!/usr/bin/env python3
"""Runner de traducción contra un llama-server dedicado, sin coordinador.

Se declara como ``TRANSLATION_RUNNER`` de ``translation_loop.py``: recibe la
misma línea de comando que ``headless-pool`` (sólo lee ``--prompt``, ``--out``
y ``--timeout``; el resto se ignora) y las rutas de los fragmentos por stdin,
una por línea. Por cada fragmento escribe ``<n>.json`` con ``result`` y una
fila ``<n>\t<ruta>`` en ``index.tsv``: el contrato que ``collect_results`` lee.

El servidor es el Ollama 0.35 que corre llama-server dentro de una unidad
propia del consumidor (``thyrox-bg start llama-direct-es-mx``). No pide
admisión ni lee cualificaciones: el modelo lo fija ``LLAMA_DIRECT_MODEL``.
Las correcciones (``NNN.correccion.md``) también pasan por aquí, así que el
mismo servidor traduce y corrige.

Como el ítem no tiene herramientas, el fragmento y su corrección van dentro
del mensaje en vez de leerse con ``Read``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translation_loop as loop  # noqa: E402

DEFAULT_URL = "http://127.0.0.1:11500"
DEFAULT_MODEL = "qwen35-9b-es-mx"
CONTEXT_TOKENS = 32768
MAX_OUTPUT_TOKENS = 12288
# «Instruct (or non-thinking) mode for general tasks» de la guía Qwen3.5-9B-GGUF —
# Llama.cpp Guides: enable_thinking=false (`think: false`) y su muestreo completo.
SAMPLING_PROFILE = "instruct-non-thinking-general"
SAMPLING = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0, "presence_penalty": 1.5,
            "repeat_penalty": 1.0}

DIRECT_NOTE = (
    "\n\n## Modo directo\n\n"
    "No hay herramientas: el fragmento (y su corrección, si existe) ya van abajo. "
    "Ignora las instrucciones de leer con `Read` o buscar con `Grep`. "
    "Responde sólo con el fragmento traducido entre `<<<ES` y `ES>>>`: la última línea "
    "de tu respuesta es `ES>>>`, no la cerca ```` que rodea al fragmento de abajo.\n"
)


def close_markers(result: str) -> str:
    """Cierra con `ES>>>` una respuesta que abrió `<<<ES` y terminó en la cerca.

    El 9B copia la cerca ```` que rodea al fragmento en el mensaje y la usa de
    cierre (lote 26, `translate/20261008T062556/`: 6 de 6 respuestas con
    `done_reason` stop rechazadas por `extract_translation`). Sólo se toca el
    marcador: si falta la apertura o ya hay cierre, el texto queda igual.
    """
    lines = result.rstrip().splitlines()
    if not lines or lines[0].strip() != "<<<ES" or any(line.strip() == "ES>>>" for line in lines):
        return result
    while lines and (lines[-1].strip().startswith("````") or not lines[-1].strip()):
        lines.pop()
    return "\n".join(lines + ["ES>>>"]) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    known, _rest = parser.parse_known_args(argv[1:] if argv and argv[0] == "headless-pool" else argv)
    return known


def build_message(template: str, zh: Path) -> str:
    """El prompt del ciclo más el fragmento y su corrección, incrustados."""
    parts = [template.rstrip(), DIRECT_NOTE, f"\nItem: {zh}\n\n## Fragmento en chino\n\n````latex\n",
             zh.read_text(encoding="utf-8"), "\n````\n"]
    correction = zh.with_name(zh.name.replace(".zh.tex", ".correccion.md"))
    if correction != zh and correction.is_file():
        parts += ["\n## Corrección de la traducción anterior (no repitas estos defectos)\n\n",
                  correction.read_text(encoding="utf-8"), "\n"]
    return "".join(parts)


def cached_result(out_dir: Path, zh: Path) -> dict | None:
    """Una respuesta válida ya obtenida para este fragmento en otra ejecución del lote.

    `collect_results` escribe los `.es.tex` sólo cuando el runner termina el
    lote entero; un reinicio del anfitrión a mitad tira lo traducido. Aquí se
    recupera de los `<n>.json` de ejecuciones anteriores, salvo que una
    corrección (`.correccion.md`) sea más nueva que esa respuesta: entonces la
    retraducción es lo que se pide.
    """
    correction = zh.with_name(zh.name.replace(".zh.tex", ".correccion.md"))
    corrected_at = correction.stat().st_mtime if correction != zh and correction.is_file() else 0.0
    for index in sorted(out_dir.parent.glob("*/index.tsv"), reverse=True):
        if index.parent == out_dir:
            continue
        for line in index.read_text(encoding="utf-8").splitlines():
            n, _, path = line.partition("\t")
            if path != str(zh):
                continue
            result_file = index.parent / f"{n}.json"
            try:
                record = json.loads(result_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if result_file.stat().st_mtime <= corrected_at:
                continue
            # Sólo una respuesta que el ciclo aceptaría: marcadores y la misma
            # estructura de entornos. Reutilizar una rechazada la repetiría
            # en cada vuelta sin volver a pedirla al modelo.
            record = {**record, "result": close_markers(record.get("result", "") or "")}
            text = loop.extract_translation(record["result"])
            if text is not None and not loop.structure_problem(zh.read_text(encoding="utf-8"), text):
                return {**record, "reused_from": str(result_file)}
    return None


def chat(url: str, model: str, message: str, timeout: int) -> dict:
    body = json.dumps({
        "model": model, "stream": False, "think": False,
        "messages": [{"role": "user", "content": message}],
        "options": {"num_ctx": CONTEXT_TOKENS, "num_predict": MAX_OUTPUT_TOKENS, **SAMPLING},
    }).encode("utf-8")
    request = urllib.request.Request(f"{url}/api/chat", data=body, headers={"Content-Type": "application/json"})
    # El servidor es local: sin el proxy de salida del entorno.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    url = os.environ.get("LLAMA_DIRECT_URL", DEFAULT_URL).rstrip("/")
    model = os.environ.get("LLAMA_DIRECT_MODEL", DEFAULT_MODEL)
    # El --timeout del ciclo (900 s) es el de un ítem agéntico. En CPU, a unos
    # 4 tokens/s, un fragmento de 5.9 KB lo agotó con prefill y salida; aquí
    # manda el plazo propio, y el del ciclo sólo si es mayor.
    timeout = max(args.timeout, int(os.environ.get("LLAMA_DIRECT_TIMEOUT", "3600")))
    template = args.prompt.read_text(encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=True)
    items = [Path(line.strip()) for line in sys.stdin if line.strip()]
    failed = 0
    with (args.out / "index.tsv").open("w", encoding="utf-8") as index:
        for n, zh in enumerate(items, start=1):
            index.write(f"{n}\t{zh}\n")
            index.flush()
            started = time.monotonic()
            reused = cached_result(args.out, zh)
            if reused is not None:
                reused["duration_s"] = 0.0
                (args.out / f"{n}.json").write_text(json.dumps(reused, ensure_ascii=False), encoding="utf-8")
                print(f"llama-direct: {n}/{len(items)} reutilizado {zh.name}", file=sys.stderr, flush=True)
                continue
            try:
                reply = chat(url, model, build_message(template, zh), timeout)
                record = {
                    "result": close_markers(reply.get("message", {}).get("content", "")),
                    "model": model, "runtime": "llama-direct", "sampling_profile": SAMPLING_PROFILE,
                    "usage": {"input_tokens": reply.get("prompt_eval_count", 0),
                              "output_tokens": reply.get("eval_count", 0)},
                    "done_reason": reply.get("done_reason"),
                }
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
                failed += 1
                record = {"result": "", "subtype": f"error: {error}", "model": model, "runtime": "llama-direct"}
            record["duration_s"] = round(time.monotonic() - started, 1)
            (args.out / f"{n}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            print(f"llama-direct: {n}/{len(items)} {record['duration_s']}s "
                  f"{'error' if 'subtype' in record else record['usage']['output_tokens']} {zh.name}",
                  file=sys.stderr, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
