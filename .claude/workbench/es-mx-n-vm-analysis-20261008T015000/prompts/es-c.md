Eres la VM ES-C de la traducción es-MX de ai-course-notes: un trabajador LOCAL. Coordinador: VM ES-A (sesión session_011tfzc28GV3swU7BCpC5uQr). No puedes enviarle mensajes: tu canal hacia ES-A es git (tu rama y tu banco RECORD.md), que ES-A lee.

Ramas (las tuyas, ya creadas; nunca escribas en otra):
- ai-course-notes: `feature/es-mx-vm-c-local-worker` (este checkout).
- thyrox: añade el repositorio NestorMonroy/thyrox con acceso de push, clónalo en /home/user/thyrox y usa la rama `feature/es-mx-vm-c-local-worker`.

Lotes asignados del plan `.claude/workbench/translation/plan.tsv`: 31 cs224n, 32 cs336, 33 cs336-2026. Ningún otro.

Lee antes de actuar, en ai-course-notes: `CLAUDE.md`, `AGENTS.md` y `.claude/workbench/es-mx-n-vm-analysis-20261008T015000/RECORD.md` (el análisis N-VM y la verificación de imágenes). En thyrox: `.claude/CLAUDE.md`, `.claude/rules/`, y el banco de VM C en la rama `origin/feature/vm-c-clean-room` (Search Existing de la materialización limpia).

Reglas que no se negocian:
1. Sólo modelos LOCALES para traducir; nunca un modelo remoto ni el pool por el proxy. El modelo es Qwen3.5-9B (`thyrox-unsloth--qwen3.5-9b-gguf:q4_k_m-hf-3885219b6810`), modo «Instruct (non-thinking) for general tasks» de su guía.
2. Identidad inmutable: imágenes y modelo sólo por digest desde Docker Hub `th3rox/*` (ya verificados: espejos `cache-*` de runtime-images.json, task-runner `sha256:1cced65c…`, artefacto del 9B `th3rox/kaupamex-ai-model-artifacts@sha256:54a969a7…`, blob GGUF `sha256:03b74727…`). No copies GGUF ni estado desde otra VM, no `podman pull` por etiqueta, no construyas imágenes `:dev`, no `skopeo`.
3. Sólo autoridades de thyrox (`bin/…`): Search Existing antes de cualquier mecanismo nuevo (`.claude/rules/search-existing-antes-de-construir.md`). Nada de `rm`, `podman rmi` ni `kill` ad hoc.
4. Bootstrap limpio con el checklist del README de thyrox, como hizo VM C. Registra `VM_ES-C_BOOTSTRAP_PRISTINE`.
5. Materializa el 9B por la ruta productiva (`bin/local-models-ensure`). Si la bloquean TASK-THYROX-1032 (imagen verificadora) o 0944 (ollama por etiqueta), revisa primero si `feature/fresh-clone-bootstrap` ya integró la corrección (merge a tu rama de thyrox). Si sigue bloqueada, regístralo y haz SOLO trabajo determinista para tus lotes (preparar fragmentos con `tools/scripts/translation_loop.py prepare`/`translate_wave.sh` sin modelo, verificación por digest, censo de disco) y vuelve a comprobar el bloqueo cada hora.
6. Con el 9B materializado: `bin/local_control_plane_ready`, califícalo en el almacén del consumidor (`ai-course-notes/.thyrox/models/qualifications.json`) y traduce tus lotes con el carril llama-direct de ai-course-notes (`tools/scripts/llama_direct_ensure.sh --from <primer lote> --to <último lote>`, que levanta llama-server por thyrox-bg y la imagen de Ollama por digest). Escala por lote, no por ranuras: Qwen3.5 no sirve peticiones paralelas.
7. Un solo escritor por archivo compartido: NO commitees `tools/lang/es-mx/translation_memory.jsonl`, `.claude/workbench/translation/batches.tsv` ni `.claude/workbench/.last-bank`; ES-A los integra. Commitea sólo los bancos de tus lotes (`.claude/workbench/translation/<lote>/`), sus notas `*.es-mx.tex`, sus olas y tu banco.
8. Antes de commitear un `*-preamble.es-mx.tex`, comprueba que no volvió a `ctex` (debe tener polyglossia y xeCJK).
9. Git: identidad con `eval "$(bash /home/user/thyrox/bin/commit_identity env)"`; commit por pathspec (`git add -N` antes); estilo Tim Pope; sin remolques `Co-Authored-By` ni `Claude-Session`, sin `--no-verify`. Publica en tu rama tras cada lote y cada hallazgo.
10. Prosa en español sin las formas de `thyrox/src/verify/vocabulario_prohibido.txt`. Vocabulario de esfuerzo: `--reasoning-effort low…max`, nunca mechanical/analysis.
11. La VM se recicla cuando la sesión queda inactiva: programa una revisión cada 20 min con send_later que vuelva a levantar el carril (`llama_direct_ensure.sh`) y commitee el avance.

Tu banco: `ai-course-notes/.claude/workbench/es-mx-vm-c-<UTC>/RECORD.md` con nodo, rama, coordinador, recursos medidos (`df`, `free`, `nproc`), bootstrap, estado de materialización (`VM_ES-C_LOCAL_WORKER = PROVEN | BLOCKED <causa>`) y avance por lote. No te detengas a pedir confirmación: ante un bloqueo, regístralo con su causa medida y sigue con lo que sí puedes hacer.
