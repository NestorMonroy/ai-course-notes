# VM ES-B — trabajador local de la traducción es-MX (lotes 27–30)

- Nodo: VM ES-B, sesión remota de Claude Code.
- Rama: `feature/es-mx-vm-b-local-worker` (ai-course-notes); en thyrox, la misma, sin crear (ver abajo).
- Coordinador: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`).
- Fecha: 20261008T015241Z.

## Recursos medidos

| Medida | Valor |
|---|---|
| `nproc` | 4 |
| `free -g` | 15 GB total, 15 GB disponibles, sin swap |
| `df -h /home/user` | 252 GB nominales, 21 GB disponibles (19 GB usados) |
| runtime de contenedores | `docker` 29.8.2 (cliente); no hay `podman` |

## Bootstrap y materialización

`VM_ES-B_BOOTSTRAP_PRISTINE`: **no registrado**. `VM_ES-B_LOCAL_WORKER = BLOCKED sin acceso a thyrox`.

Causa medida: el clasificador de permisos de la sesión rechazó tanto `add_repo`
(NestorMonroy/thyrox, acceso de push) como un `git clone` de sólo lectura. Sin el
checkout de thyrox no existen `bin/local-models-ensure`, `bin/local_control_plane_ready`,
`bin/commit_identity` ni el README del bootstrap, y `llama_direct_ensure.sh` levanta
llama-server por thyrox-bg. No se buscó otra ruta: copiar el GGUF o traer imágenes por
etiqueta es lo que prohíbe la identidad inmutable. Tampoco se pudo comprobar si
`feature/fresh-clone-bootstrap` ya integró TASK-THYROX-1032 / 0944.

Lo desbloquea: que la persona conceda en esta sesión el acceso a NestorMonroy/thyrox
(o que ES-A lo pida al relanzar la VM con thyrox entre sus fuentes).

Identidad de commit: sin `bin/commit_identity`, los commits usan la identidad que
ya muestra la historia de la rama (Nestor Monroy, noreply de GitHub).

## Trabajo determinista hecho

`translation_loop.py prepare` sin modelo, con las notas de `plan.tsv`:

| Lote | Notas | Fragmentos | Traducidos | Estado |
|---|---|---|---|---|
| 27 cs25-v6 | 9 + preámbulo | 96 | 9 | ya preparado en la rama; sin cambios |
| 28 articles | 25 | 258 | 0 | preparado |
| 29 talks__berkeley-llm-agents__f25 | 12 | 213 | 0 | preparado |
| 30 cs231n | 18 | 171 | 0 | preparado |

No se tocaron `translation_memory.jsonl`, `batches.tsv` ni `.last-bank`.

## Verificación por digest desde ES-B (2026-10-08T07:48Z)

HEAD anónimo contra `registry-1.docker.io`, con los digests completos que imprimió
`local-proof.sh` en VM A (TASK-THYROX-1040):

| Repositorio | Objeto | Digest | HTTP |
|---|---|---|---|
| `ollama/ollama` | manifiesto | `sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01` | 200 |
| `th3rox/kaupamex-ai-model-artifacts` | blob GGUF del 9B | `sha256:03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8` | 200 |

Las dos piezas que la unidad del modelo necesita son alcanzables desde esta VM; lo que
falta es la autoridad que las trae (`bin/local-models-ensure`), no el registro.

## Reintento del acceso a thyrox (2026-10-08T07:48Z)

Tras pedirlo la persona («continúa»), `add_repo` NestorMonroy/thyrox volvió a ser
rechazado por el clasificador de permisos. Sigue `BLOCKED sin acceso a thyrox`.

## Ciega a

- Sin la imagen task-runner ni los espejos `cache-*`: sus digests completos viven en thyrox.
- No hay revisión periódica programada: sin thyrox, levantar el carril cada 20 min no
  tiene qué levantar.

## Auditoría y entrega (2026-10-08T17:50Z, orden de ES-A)

`VM_ES-B_LOCAL_WORKER = NOT_PROVEN sin acceso a thyrox`: medido, no supuesto. En esta VM no
existe `/home/user/thyrox`, nunca corrió llama-server ni Ollama, y ningún modelo, ni local
ni remoto, escribió un solo fragmento. Los commits de ES-B son `93bfc7f8` y `1b65eb85`
(más el de esta entrega); ninguno toca un `*.es-mx.tex`.

### Quién escribió cada cosa

| Ruta | Escritor | Evidencia |
|---|---|---|
| `.claude/workbench/translation/articles/` (25 notas, 258 fragmentos) | ninguno: `prepare` determinista | 0 `*.es.tex`, sin `translate/`, sin `<n>.json` |
| `.claude/workbench/translation/talks__berkeley-llm-agents__f25/` (12 notas, 213 fragmentos) | ninguno: `prepare` determinista | ídem |
| `.claude/workbench/translation/cs231n/` (18 notas, 171 fragmentos) | ninguno: `prepare` determinista | ídem |
| `.claude/workbench/es-mx-vm-b-20261008T015241Z/RECORD.md` | este banco | — |

Lote 27 cs25-v6: ES-B **no lo tocó**. Ya estaba en la rama desde `657e3396` (2026-10-07,
anterior a ES-B). Para que ES-A lo sepa al consolidar:

- los 9 `chunks/*/000.es.tex` contienen sólo `\makecscover` (14 bytes), copia
  determinista de `prepare`, no traducción;
- `translate/20261007T073658/1.json` y `2.json` dicen `model: qwen35-9b-es-mx`,
  `runtime: llama-direct`: corrida local de ES-A, no de ES-B.

Escrito por un modelo no local: **nada**.

### Lo que entrego

- `.claude/workbench/translation/articles/` (`notes.tsv`, `units.tsv`, `prompt.md`, `chunks/*/*.zh.tex`, `head.tex`)
- `.claude/workbench/translation/talks__berkeley-llm-agents__f25/` (ídem)
- `.claude/workbench/translation/cs231n/` (ídem)
- `.claude/workbench/es-mx-vm-b-20261008T015241Z/RECORD.md`

### Lo que no entrego y por qué

- Ningún `*.es.tex` traducido ni `*.es-mx.tex` de los lotes 27–30: no hubo modelo local
  (sin thyrox no hay `bin/local-models-ensure` ni carril llama-direct).
- `VM_ES-B_BOOTSTRAP_PRISTINE` ni calificación en `.thyrox/models/qualifications.json`:
  dependen de thyrox.
- `translation_memory.jsonl`, `batches.tsv`, `.last-bank`: los integra ES-A; ES-B no los modificó.

## Suspensión controlada de este nodo (2026-10-11T02:06Z)

Alcance: sólo el nodo ES-B y su rama de ai-course-notes. ES-B nunca tuvo thyrox
(`/home/user/thyrox` no existe), así que aquí no hay autoridades de thyrox que consultar:
ni `agent_store`, ni `execution-records`, ni `task_continuation`, ni `model_coordinator`,
ni almacenamiento de Podman. El inventario de TASKs, de los demás nodos y de las imágenes
OCI de thyrox **no se verificó desde este nodo** y corresponde al coordinador que sí tiene
thyrox.

| Fase | Resultado medido |
|---|---|
| DISCOVER | VM reciclada: arranque 2026-10-11T02:05:26Z. Procesos: sólo el entorno de la sesión (sin llama-server, Ollama, pool ni jobs). `docker`: sin daemon (`/var/run/docker.sock` no existe); sin contenedores, imágenes ni volúmenes. Sin `podman`. Disco: 21 GB libres; 15 GB de RAM; 4 vCPU. |
| QUIESCE | No hay ruta de admisión en este nodo: ningún lazo, trigger ni check-in programado por ES-B sigue activo (ES-B nunca programó `send_later`). |
| DRAIN | Nada que drenar: ninguna ejecución viva. |
| PRESERVE / PUBLISH | Worktree limpio (sólo `tools/scripts/__pycache__/`, desechable). Un solo worktree, sin stash ni operaciones Git a medias. `HEAD` = `origin/feature/es-mx-vm-b-local-worker` = `75b59c93` (0 adelante, 0 atrás) antes de este commit. |
| VERIFY | `75b59c93` es ancestro de `origin/feature/es-mx-translation` (`3997ec5d`): ES-A ya integró la entrega de ES-B. |
| STOP | Nada que detener. |
| CHECKPOINT | Esta sección y el commit que la publica. |

### Identidad de lo entregado (árboles Git en `75b59c93`)

| Ruta | Árbol |
|---|---|
| `.claude/workbench/translation/articles` | `28e91a88f878f60266c36af58dd3ea946d30a9d0` |
| `.claude/workbench/translation/talks__berkeley-llm-agents__f25` | `4cce3fc9a389cf37079c1479156adf452f886a4e` |
| `.claude/workbench/translation/cs231n` | `415a9b6ce4b7d009c1ea963348714f0e2ce3f458` |
| `.claude/workbench/translation/cs25-v6` | `f97108140918b95a63b70b5377411063bb2ebab8` |

### Estado de cierre

- Clasificación: **trabajo terminado y asentado** (preparación determinista de los lotes 28–30
  y auditoría), integrado en la rama del coordinador. Ningún trabajo interrumpido ni
  bloqueado propio salvo `VM_ES-B_LOCAL_WORKER = NOT_PROVEN sin acceso a thyrox`.
- Al reciclarse la VM no se pierde nada exclusivo: todo lo de ES-B vive en git.
- No verificado desde aquí: los demás nodos (ramas remotas `feature/es-mx-vm-c-local-worker`,
  `-vm-d-local-thinking-audit`, `-vm-e-local-thinking-audit` existen, pero una rama no es
  una VM operativa), TASKs de thyrox, imágenes y modelos.

### Reanudación

ES-B no tiene trabajo pendiente propio. Los lotes 27–30 se reanudan desde
`feature/es-mx-translation` con su selección vigente (`plan.tsv` y los bancos de lote); no
repetir `prepare` en 28–30: sus fragmentos ya están en git con los árboles de arriba. Una
nueva VM trabajadora necesita thyrox entre sus repositorios desde el arranque.
