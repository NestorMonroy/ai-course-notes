# VM ES-C — trabajador local de la traducción es-MX (lotes 31–33)

- Nodo: VM ES-C, sesión remota de Claude Code.
- Rama: `feature/es-mx-vm-c-local-worker` (ai-course-notes); en thyrox la misma, sin clon.
- Coordinador: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`).
- Fecha: 2026-10-08T01:59Z.

## Recursos medidos

| Medida | Valor |
|---|---|
| `nproc` | 4 |
| `free -g` | 15 GB total, sin swap |
| `df -h /` | 252 GB, 21 GB disponibles (asignación de la sesión) |
| motor de contenedores | `docker` 29.8.2; Podman 4.9.3 instalado por el toolchain de thyrox |

## Bootstrap (07:50Z, tras «Intentar nuevamente» del ejecutor)

`VM_ES-C_BOOTSTRAP_PRISTINE = YES`. thyrox se adjuntó al reintentar (`add_repo` push) y se clonó
en `/home/user/thyrox`; estado inicial medido: sin `~/.thyrox`, sin `.thyrox/runtime`, sin
`.env`, sin Podman, 0 imágenes.

Checklist del README, como VM C: `write-env.sh` → identidad del commit en `.env`
(`.claude/rules/git.md`) → `uv sync` y `bun install` (587 paquetes, exit 0) →
`check_env_contract_keys --strict` (0 sin declarar) → `scripts/install-hooks.sh`
(`core.hooksPath=.githooks`) → toolchain con `THYROX_INSTALL_{PARALLEL,GNU_TIME,PODMAN,GAWK}=1`
(exit 0 los cuatro; Podman 4.9.3, overlay, sqlite).

`bin/declarations` y `check_githooks_activos` rehúsan: `THYROX_REACH_ROOTS` no declarada y no
derivable (los hermanos `thyrox` y `ai-course-notes` no comparten prefijo). No bloquea la
materialización.

Rama de thyrox: `feature/es-mx-vm-c-local-worker` con `origin/feature/fresh-clone-bootstrap`
integrada (`2156f9cc2`): trae las correcciones de TASK-THYROX-1032 (`7dd5fc784`, `5fa19322d`) y
0944 (`95e2c5ae5`, `0ff814b94`). Publicada.

## Materialización del 9B

`bin/local-models-ensure thyrox-unsloth--qwen3.5-9b-gguf:q4_k_m-hf-3885219b6810` lanzado a las
07:58Z sobre `2156f9cc2`. Disco libre al lanzar: 17 571 332 096 B. VM C estimó la cadena
completa en ≈20,8 GB (con copia en el almacén de Ollama, supuesta): puede no caber.

Resultado: `status failed`, `stage materialize`, `downloaded false`, `installed false`:
`rate_limited: 429 Too Many Requests {"kind":"pull-rate","limit":100,"remaining":0,
"windowSeconds":3600,"source":"160.79.106.143"}`. Docker Hub agotó la cuota de *pulls* de la IP
de salida (compartida con las otras VMs, ventana de 1 h). El disco bajó de 17 GB a 11 GB
durante la ejecución: algo se trajo antes del 429 (sin medir qué).

`VM_ES-C_LOCAL_WORKER = BLOCKED docker-hub-429-pull-rate` (no 1032 ni 0944). Se reintenta
pasada la ventana; con 11 GB libres puede no caber el resto de la cadena.

## Avance por lote (trabajo determinista, sin modelo)

`translation_loop.py prepare` por lote, sin `advance` ni barrido; no toca
`translation_memory.jsonl`, `batches.tsv` ni `.last-bank`.

| Lote | Notas | Fragmentos | Traducidos | Preámbulo con `ctex` |
|---|---|---|---|---|
| 31 cs224n | 17 | 165 | 0 | no |
| 32 cs336 | 17 | 250 | 0 | no |
| 33 cs336-2026 | 19 (incluye `cs336-preamble`) | 210 | 0 | no |

## Ciega a

- No se midió nada de thyrox ni de Docker Hub desde esta VM.
- No se verificó la prosa contra `vocabulario_prohibido.txt` (vive en thyrox).
