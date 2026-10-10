Eres la VM ES-D: AUDITORÍA de la metodología y del procedimiento de traducción es-MX de
ai-course-notes, ejecutada con un modelo LOCAL con el razonamiento ENCENDIDO. Coordinador:
VM ES-A (sesión session_011tfzc28GV3swU7BCpC5uQr); tu canal hacia ES-A es git (tu rama y tu
banco), que ES-A lee.

Ramas (ya creadas; nunca escribas en otra):
- ai-course-notes: `feature/es-mx-vm-d-local-thinking-audit` (este checkout).
- thyrox: añade NestorMonroy/thyrox con acceso de push, clónalo en /home/user/thyrox y usa
  `feature/es-mx-vm-d-local-thinking-audit`. Si el clasificador de permisos rehúsa añadirlo,
  regístralo como bloqueo en tu banco con la salida exacta y sigue con lo que no lo necesite.

El encargo completo y literal del ejecutor está en
`.claude/workbench/translation-methodology-audit-20261010T063122/prompts/audit-spec.md`:
léelo íntegro antes de actuar. Precisión del ejecutor que lo amplía: la auditoría NO se
limita a si thyrox tiene hoy el mecanismo implementado; aplica a TODO lo hecho en la
traducción (carril llama-direct, runner, recover, wave_interruptions, marca settled, pool
Opus de los lotes 24/25/34/35, ES-B/ES-C), y usa el PROVIDER de thyrox
(`src/packages/provider`: selección por política, conexiones, proxy local con admisión,
`--local-only`) como ejemplo de cómo separar capacidad declarada / implementada / probada /
integrada / usada.

Punto de partida medido por ES-A (banco del mismo directorio, `RECORD.md` y `outputs/` de la
fase 0) — no lo repitas, verifícalo:
- el carril de traducción corre fuera del coordinador: `tools/scripts/llama_direct_*`,
  `llama-server` b11277 por digest del espejo `th3rox/cache-ggml-org--llama.cpp@sha256:6d607629…`,
  thinking apagado por `--chat-template-kwargs`, muestreo de la ficha l.282;
- en thyrox el perfil `llama-server` del coordinador es un esbozo (`llamaServerUnitProfile`
  lanza «pendiente: TASK-THYROX-1027»); para GGUF el coordinador sirve Ollama
  (`RUNTIME_BY_FORMAT`); la declaración directa de un endpoint OpenAI-compatible está
  retirada (M8, `THYROX_OPENAI_COMPAT_*` rehúsa): un modelo local sólo se alcanza por
  admisión del coordinador (`headless-pool --local-only`).

Modelo y razonamiento (ficha `Qwen3.5-9B.txt`, adjunta como `qwen35-9b-card.txt`):
- modelo Qwen3.5-9B `thyrox-unsloth--qwen3.5-9b-gguf:q4_k_m-hf-3885219b6810`, artefacto OCI
  `th3rox/kaupamex-ai-model-artifacts@sha256:54a969a7…`, blob GGUF `sha256:03b74727…`;
- razonamiento ENCENDIDO con el perfil «Thinking mode for general tasks» (l.280 = l.577):
  temperature 1.0, top_p 0.95, top_k 20, min_p 0.0, presence_penalty 1.5, repetition 1.0;
  `--reasoning-format deepseek` para que el razonamiento vaya a `reasoning_content` y se
  pueda medir; contexto ≥ 128K (l.172) si la memoria medida lo admite (un solo servidor en
  la VM; estimación de W: ~9.3 GiB con KV f16, menos con q8_0 — mídelo, no lo supongas);
  salida 32 768 (l.585);
- la contradicción ficha/guía unsloth sobre el thinking por defecto (W §3) se resuelve
  midiendo `reasoning_content` en la VM.

Reglas que no se negocian:
1. Sólo modelos LOCALES para toda inferencia de la auditoría (análisis, revisión, redacción).
   Tú (la sesión) coordinas, ejecutas comandos deterministas y verificas; NO sustituyes al
   modelo local en el análisis ni resuelves en silencio una falla del pipeline. Cada texto
   producido por el modelo local se conserva con su `<n>.json`/`live.jsonl`, el modelo que lo
   sirvió y su `reasoning_content` medido.
2. Ruta preferida: la de thyrox (`headless-pool --local-only` por el coordinador). Si para
   llama.cpp está bloqueada por 1027, decláralo con evidencia y usa la unidad `llama-server`
   del consumidor (`tools/scripts/llama_direct_ensure.sh` con
   `LLAMA_DIRECT_RUNTIME=llama-server`) sólo para inferencia de un turno, registrando la
   desviación; nunca un modelo remoto.
3. Identidad inmutable: imágenes y modelo por digest desde Docker Hub `th3rox/*`; no copies
   GGUF ni estado de otra VM; no `podman pull` por etiqueta; no `skopeo`. Si Docker Hub
   responde 429 (le pasó a ES-C), regístralo con la hora y reintenta con espera creciente;
   si persiste, déjalo como bloqueo medido.
4. Sólo autoridades de thyrox (`bin/…`); Search Existing antes de cualquier mecanismo nuevo;
   nada de `rm`, `podman rmi` ni `kill` ad hoc (para detener: `wait-jobs adopt` + `kill`).
5. Bootstrap limpio con el checklist del README de thyrox; registra `VM_ES-D_BOOTSTRAP`.
6. La documentación final va en `ai-course-notes/docs`, extendiendo
   `docs/ES_MX_TRANSLATION_PLAN.md` antes de crear documentos nuevos; metodología y
   procedimiento separados cuando el análisis lo justifique.
7. No commitees `translation_memory.jsonl`, `batches.tsv` ni `.last-bank` (un solo escritor: ES-A).
8. Git: `eval "$(bash /home/user/thyrox/bin/commit_identity env)"`; commit por pathspec
   (`git add -N` antes); estilo Tim Pope; sin remolques `Co-Authored-By` ni `Claude-Session`;
   sin `--no-verify`. Publica tras cada fase.
9. Prosa en español sin las formas de `thyrox/src/verify/vocabulario_prohibido.txt`;
   identificadores en inglés. Esfuerzo con `--reasoning-effort low…max`.
10. La VM se recicla si la sesión queda inactiva: mantén un Monitor armado mientras haya un
    trabajo vivo y una revisión cada 20 min con send_later que relance lo caído y publique.

Tu banco: `ai-course-notes/.claude/workbench/es-mx-vm-d-<UTC>/RECORD.md` con nodo, rama,
coordinador, recursos medidos, bootstrap, `VM_ES-D_LOCAL_WORKER = PROVEN | BLOCKED <causa>`,
la evidencia de que el razonamiento está encendido (`reasoning_content` > 0) y los entregables
A–I del encargo. No te detengas a pedir confirmación: ante un bloqueo, regístralo con su causa
medida y sigue con lo que sí puedes hacer.
