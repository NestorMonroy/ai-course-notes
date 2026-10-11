# suspension-checkpoint — punto de reanudación de la traducción es-MX y de sus nodos

**Léase primero.** Este banco es el checkpoint canónico de la suspensión
controlada del 2026-10-11. Responde una sola pregunta: qué quedó preservado,
dónde, y cómo se reanuda sin repetir trabajo. Todo dato de abajo sale de un
archivo de `outputs/` o de un commit citado; nada sale de la memoria del
coordinador que lo escribió.

## El encargo

Texto íntegro del ejecutor en [`prompts/suspension-spec.md`](prompts/suspension-spec.md).
Su primera parte —integrar `feature/fresh-clone-bootstrap` en la rama de
thyrox— se hizo antes de suspender: merge `a95811683` (125 commits, el store
unido por `merge_sqlite_union` sin conflictos), publicado en
`feature/ai-course-notes-l1`.

## Resumen ejecutivo

| | |
|---|---|
| Checkpoint | 2026-10-11, descubrimiento 02:00Z (`outputs/discovered-at.txt`), cierre 02:1xZ |
| Repositorios | ai-course-notes `feature/es-mx-translation`; thyrox `feature/ai-course-notes-l1` (`outputs/repositories.tsv`) |
| Estado del cierre | **SUSPENSIÓN PARCIAL VERIFICADA**: ver «Criterios» abajo; lo no verificado está nombrado |
| Objetivo padre | autonomía local de extremo a extremo con modelos locales; veredicto de ES-G: **no probado** (rama thyrox `feature/p0-conformance-validation`, banco `p0-conformance-validation-20261010T194549`, sección G) |
| Traducción | 4 203 fragmentos, 2 947 traducidos, 1 256 pendientes en los lotes 27–33 (`outputs/translation-progress.tsv`) |
| TASKs del store | 1 256 `completed`, 107 `in_progress`, 1 265 `pending` (`outputs/tasks-by-status.tsv`); 42 claims vivos (`outputs/claims-live.tsv`) |
| Barrera | marca `settled 27 33 … suspension` en `.claude/cache/waves/llama-direct.settled`; rutinas de revisión borradas; coordinador sin admisión |

## Lo que hace cada pieza

| archivo | qué es |
|---|---|
| `probes/discover.sh` | descubrimiento de solo lectura; se vuelve a ejecutar tal cual en una reanudación o en una segunda suspensión |
| `outputs/repositories.tsv`, `worktrees.txt`, `remote-branches.tsv` | ramas, HEAD, divergencia, cambios y worktrees de los dos repos |
| `outputs/nodes.tsv` | cada nodo (sesión), su papel, su rama y su estado de suspensión |
| `outputs/tasks-by-status.tsv`, `tasks-open.tsv`, `claims-live.tsv` | TASKs del store versionado (lectura `mode=ro`) y claims del ledger `.claude/coordination/claims.jsonl` de thyrox |
| `outputs/jobs-ledger.txt`, `processes.txt` | ledger de `wait-jobs` y procesos vivos en el momento del descubrimiento |
| `outputs/podman-*.tsv`, `podman-image-labels.tsv` | imágenes (las sin etiqueta incluidas), contenedores, volúmenes, pods, versión |
| `outputs/oci-remote-verification.tsv` | qué identidad OCI está verificada en remoto y con qué evidencia |
| `outputs/models.tsv`, `model-registry-files.sha256`, `local-artifacts.tsv` | catálogo de modelos, su GGUF local, su copia OCI y sus cualificaciones |
| `outputs/stores.tsv`, `volume-*.sha256` | almacenes durables con su hash; manifiesto por archivo de los volúmenes de Podman |
| `outputs/translation-progress.tsv` | fragmentos fuente y traducidos por lote |
| `outputs/preserved-salvage/` | parche rescatado del pool que sólo vivía en `.thyrox/` (ignorado por git) |
| `outputs/settled-marker-before-suspension.tsv` | la marca anterior (lote 26), antes de sobrescribirla con la barrera |
| `SHA256SUMS` | integridad de todo el banco |

## Decisiones que no se reabren

Cada una con su autoridad; ninguna es recomendación nueva.

- Sólo modelos **locales** para todo trabajo generativo; Claude no es respaldo
  generativo — `thyrox/.claude/rules/local-work-validation.md`, política
  `execution_policy.json` sin `fallbackModels`.
- Podman como primitiva de ejecución (**ADR-007**, registro de gobierno
  `kaupamex-docs: source/gestion/pm/docs/iniciativas/actualizar-agentic-ai-thyrox/`,
  no accesible desde esta sesión); acceso a Podman sólo por
  `src/packages/podman-execution/` (gates `check_podman_*` del pre-commit).
- Autoridades existentes antes que mecanismo nuevo —
  `thyrox/.claude/rules/search-existing-antes-de-construir.md`.
- Imágenes y pesos se traen **por digest** desde Docker Hub `th3rox/*`; el GGUF
  es un artefacto OCI aparte de las imágenes (`.thyrox/models/artifact-locations.json`).
- Lectura y publicación usan credenciales distintas: lectura
  `THYROX_REGISTRY_READER_USERNAME`/`_TOKEN` (`readerCredential.ts`), publicación
  `THYROX_REGISTRY_PUBLISHER_TOKEN` (`registry-credentials/registryCredential.ts`).
  `DOCKER_PAT_RW` no es reconocido por el publisher;
  `THYROX_REGISTRY_READER_WRITE_TOKEN` no tiene consumidor.
- Carril de traducción: llama.cpp `llama-server` b11277, imagen
  `th3rox/cache-ggml-org--llama.cpp@sha256:6d607629…`, Qwen3.5-9B con el
  razonamiento apagado y el muestreo de la ficha (l.282), `--cache-ram 0`
  (`ai-course-notes/tools/scripts/llama_direct_ensure.sh`, commits `0e619951`,
  `28fcaa9a`, `f2b2271e`).
- Identificadores en inglés, prosa en español —
  `thyrox/.claude/rules/identificadores-en-ingles.md`.

## Trabajo hecho, interrumpido y pendiente

| línea | estado | dónde |
|---|---|---|
| Traducción lotes 1–26 | hechos | `outputs/translation-progress.tsv` (pendiente 0) |
| Traducción lote 27 (cs25-v6) | 100/105; el último fragmento admitido (`lecture09/006`) terminó en el drenaje | commit `94653bd5` |
| Traducción lotes 28–33 | pendientes (16/258 de articles; 0 en los otros cinco) | `outputs/translation-progress.tsv` |
| Auditoría de la traducción (ES-F) | A, B, C, D, E, F, H hechos; G e I **interrumpidos** con su prompt y punto de reanudación | thyrox `feature/es-mx-vm-f-local-thinking-audit`, `RECORD.md` sección «Suspensión» (`61bd9be7b`) |
| Validación de conformidad del P0 (ES-G) | completa (§20, A–G); veredicto: autonomía **no probada** | thyrox `feature/p0-conformance-validation` (`3bf814298`, `238197bf2`) |
| Consolidación de A–I en `ai-course-notes/docs` | pendiente: espera G e I de ES-F | — |
| Merge de `fresh-clone-bootstrap` | hecho, publicado; **suite no ejecutada** sobre el merge | thyrox `a95811683` |

## Lo que no se pudo verificar

- **Manifest remoto** de `thyrox-task-runner`, `ai-course-notes-runner` y del
  segundo digest del espejo de llama.cpp: no hay autoridad de solo lectura
  para consultarlo (`outputs/oci-remote-verification.tsv`). El espejo de
  llama.cpp y el artefacto del 9B sí: ES-F y ES-G los bajaron en frío.
- **Publicación OCI bloqueada**: `THYROX_REGISTRY_PUBLISHER_TOKEN` ausente. Las
  10 imágenes `permanent` y la `thyrox-transformers-runtime:dev` local quedan
  conservadas en el almacenamiento de Podman de este nodo, no en remoto.
- **PostgreSQL**: el volumen `thyrox-postgres-data` (46 MB) está detenido y es
  consistente ante caída; no hay autoridad de respaldo (`pg_dump`) en thyrox.
  Queda con su manifiesto por archivo (`outputs/volume-thyrox-postgres-data.sha256`),
  sólo local.
- **Nodos del P0 fuera de esta cuenta** (VM A, E, G, K, L, M, N, O, R, W): sólo
  sus commits son visibles; sus 42 claims vivos no se liberaron
  (`outputs/claims-live.tsv`). No se reasigna ninguna TASK suya.
- **Contenedores obsoletos**: `thyrox-postgres`, `thyrox-redis`,
  `thyrox-ollama` y `thyrox-worker-workbench-mv2sqc6y-5813` aparecen
  `running` en Podman pero son de antes del reclamo de las 00:32Z (exec falla:
  «stopped container»). No se tocaron.
- **Modelos sin copia durable**: `qwen2.5-coder-7b` y `phi-4-mini` no tienen GGUF
  local ni ubicación OCI (`outputs/models.tsv`).

## Cómo se reanuda

En este orden; ningún paso ejecuta una TASK antes del 9.

1. `cd ai-course-notes/.claude/workbench/suspension-checkpoint-20261011T015832 && sha256sum -c SHA256SUMS`.
2. Leer este README; no hace falta releer conversaciones ni logs.
3. `bash probes/discover.sh` en una copia del banco o con otra salida, y
   comparar con `outputs/`: lo que cambió es actividad posterior al
   checkpoint y se reconcilia antes de seguir.
4. En thyrox: `bin/local_control_plane_ready` (coordinador, Postgres, Redis).
5. Comprobar que ningún lazo ni servidor anterior sigue vivo:
   `bash bin/wait-jobs status`, `pgrep -fa '[l]lama_direct_loop'`.
6. El 9B está en `.thyrox/models/artifacts/sha256-03b74727….gguf`; si falta,
   se materializa por digest desde `th3rox/kaupamex-ai-model-artifacts@sha256:54a969a7…`,
   nunca de Hugging Face.
7. **Liberar la barrera**: retirar la línea `27 33 … suspension` de
   `ai-course-notes/.claude/cache/waves/llama-direct.settled`.
8. `bash tools/scripts/llama_direct_ensure.sh` levanta el servidor y el lazo
   desde el lote 27; reutiliza las respuestas aceptadas (`cached_result`), no
   las vuelve a pedir.
9. Para el P0: la siguiente TASK la elige `task_continuation` con los
   mecanismos vigentes, no este README.
10. ES-F: retomar G e I desde su sección «Suspensión»; consolidar A–I en
    `docs/ES_MX_TRANSLATION_PLAN.md`.

## Criterios del encargo (§18)

| | resultado |
|---|---|
| A Descubrimiento | cumplido; lo desconocido está nombrado arriba |
| B Preservación | cumplido en git para código, progreso, evidencia y decisiones; Postgres sólo local |
| C Imágenes OCI | **parcial**: publicación bloqueada por credencial; imágenes conservadas, nada se borró |
| D Modelos | cumplido para el 9B (local y OCI verificado); 2 modelos del catálogo sin copia durable |
| E Integridad | `SHA256SUMS` verificado tras escribirlo |
| F Detención | ES-A: lazo y servidor detenidos con `wait-jobs`; ES-G detenido; ES-F en espera de su commit final de detención; `thyrox-ollama` de ES-G sin comando de parada en thyrox |
| G Reanudación | procedimiento de arriba |
| H Idempotencia | `discover.sh` sólo lee; la barrera es una marca que se sobrescribe igual; ningún paso crea TASKs ni publica |

*Métrica:* inventarios por clase leídos con las autoridades de thyrox, y
`SHA256SUMS` sobre el banco.
*Ciega a:* el estado interno de los nodos de otras cuentas, el contenido
remoto de las imágenes sin verificación en frío y la consistencia lógica de
Postgres sin abrirlo.
