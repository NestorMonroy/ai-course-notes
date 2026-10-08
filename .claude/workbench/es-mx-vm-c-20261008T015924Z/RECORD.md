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

## Auditoría y entrega (17:52Z, orden de ES-A)

### Qué modelo escribió cada cosa

**Ningún modelo, ni local ni remoto, escribió nada en esta VM.** Todo lo producido es
preparación determinista (`translation_loop.py prepare`) y prosa de este banco.

Evidencia, medida a las 17:52Z:

| Comprobación | Resultado |
|---|---|
| resultados `<n>.json` en los bancos de los lotes 31–33 | 0 |
| archivos bajo `translate/` en esos bancos | 0 (el directorio no existe) |
| `*.es-mx.tex` / `*.es.tex` nuevos en `cs224n/`, `cs336/`, `cs336-2026/` | 0. El único que existe, `cs336-2026/cs336-preamble.es-mx.tex`, es de `601603ae` (2026-10-05), anterior a esta VM |
| `local-models-ensure` | `failed`, `downloaded false`, `installed false` (429 de Docker Hub) |
| `llama_direct_ensure.sh`, `translate_wave.sh`, `advance` | nunca ejecutados |

`VM_ES-C_LOCAL_WORKER = NOT_PROVEN docker-hub-429-pull-rate`: no hay GGUF ni unidad
`model-runtime`, así que no hay cadena de procedencia que medir.

Escrito por un modelo no local: nada.

Lo que sí se trajo antes del 429, todo por digest, que explica la bajada de disco a 11 GB:
`th3rox/thyrox-task-runner@sha256:1cced65c…` (386 MB), `ollama/ollama@sha256:2a6e883b…`
(5,51 GB), `th3rox/cache-library--ubuntu@sha256:a853f94d…` (80,7 MB). Viven en el Podman de
esta VM; no se publican y desaparecen con ella.

### Lo que entrego (rama `feature/es-mx-vm-c-local-worker`)

| Ruta | Contenido |
|---|---|
| `.claude/workbench/translation/cs224n/` | `notes.tsv`, `units.tsv`, `chunks/` (17 notas, 165 fragmentos) |
| `.claude/workbench/translation/cs336/` | ídem (17 notas, 250 fragmentos) |
| `.claude/workbench/translation/cs336-2026/` | ídem (19 notas con `cs336-preamble`, 210 fragmentos) |
| `.claude/workbench/es-mx-vm-c-20261008T015924Z/RECORD.md` | este banco |
| thyrox `feature/es-mx-vm-c-local-worker` @ `2156f9cc2` | merge de `feature/fresh-clone-bootstrap` (1032, 0944) |

Los `head.tex` preparados no contienen `ctex`.

### Lo que NO entrego, y por qué

- Ninguna traducción (`*.es-mx.tex`, fragmentos traducidos, olas): el 9B no se materializó.
- `translation_memory.jsonl`, `batches.tsv`, `.last-bank`: no se tocaron (un solo escritor, ES-A).
- Cualificación en `.thyrox/models/qualifications.json`: sin modelo, no hay qué calificar.
- `.env` de thyrox (identidad y rutas de esta VM): ignorado por git, local al nodo.

### Pendiente para ES-A

- Los commits `0580f5a1` y `372c547a` salieron con la identidad por defecto del contenedor
  (author `Kim`), no la de `.claude/rules/git.md`: faltaba cargar el `.env` de thyrox antes de
  `commit_identity env`. Reescribirlos exige *force-push*, que el clasificador de permisos
  rehusó; se deja a ES-A o al ejecutor. Los commits posteriores tienen la identidad correcta.
