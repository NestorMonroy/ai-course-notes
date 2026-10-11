# ES-C: suspensión controlada del nodo y punto de reanudación

- Nodo: VM ES-C (sesión remota de Claude Code), trabajador local de la traducción es-MX.
- Coordinador declarado: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`); no se le puede
  enviar mensajes desde aquí: el canal es git.
- Checkpoint: 2026-10-11T02:09:42Z (`date -u`). El nodo se reinició a las 2026-10-11T02:06Z
  (`uptime -s`); el último trabajo fue el 2026-10-08.
- Dónde vive: en ai-course-notes, porque el trabajo de ES-C es la traducción de este repo; en
  thyrox sólo queda el commit de `bun.lock`. El directorio
  `thyrox:.claude/workbench/suspension-checkpoint-20261011T015832` que nombró el ejecutor no
  existe en este nodo (ni en disco ni en la historia del clon): lo escribió otra sesión.
- Alcance: **sólo este nodo**. No hay autoridad desde aquí para descubrir ni suspender otras
  VMs; las demás quedan como no verificadas por este registro.

## Resumen de reanudación

ES-C no tiene trabajo generativo en curso ni interrumpido. Su única tarea (traducir los lotes
31 cs224n, 32 cs336 y 33 cs336-2026 con Qwen3.5-9B local) quedó **bloqueada antes de empezar**:
`local-models-ensure` falló con un 429 de *pull-rate* de Docker Hub. Los lotes están preparados
de forma determinista y entregados a ES-A (`ai-course-notes@b1061513`, «Hand over ES-C work to
ES-A»). Ningún modelo, local ni remoto, escribió nada en este nodo.

Para reanudar: no hay que repetir nada de lo de abajo. La siguiente acción la elige ES-A
(consolidación desde `feature/es-mx-vm-c-local-worker`) o, en thyrox, `task_continuation`;
este registro no fija ninguna TASK.

## Inventario (medido en el checkpoint)

### Repositorios

| Repo | Rama | HEAD local = remoto (`ls-remote`) | Árbol | Pendiente |
|---|---|---|---|---|
| ai-course-notes | `feature/es-mx-vm-c-local-worker` | `b1061513` | `499cc6b9` | nada |
| thyrox | `feature/es-mx-vm-c-local-worker` | `2156f9cc2` antes del commit de `bun.lock` | `3b424444` | `bun.lock` |

Sin worktrees adicionales, sin stash, sin operaciones git a medias en ninguno de los dos.
`feature/fresh-clone-bootstrap` avanzó a `701cefb6` después del merge (`2156f9cc2`): **no se
integra en el cierre**, queda como divergencia conocida.

`bun.lock`: `bun install` (paso 1b del checklist) añadió `@thyrox/image-registry` a las
dependencias de un paquete que ya la declaraba en su `package.json`: es la salida de la
herramienta del repo, no una edición a mano. Se commitea en thyrox, en su propio commit.

`.claude/jobs/model-coordinator-20261008T175018/`: lanzamiento de `bin/model_coordinator run`
que hizo `local-models-ensure` el 2026-10-08 17:50:18Z. No se versiona: `check_bench_untracked`
exige todo el directorio, incluido `outputs/pid` (pid 3890, muerto tras el reinicio), y un pid
versionado es el defecto N-VM de H-THYROX-575. Su `README.md` y `manifest.jsonl` se copiaron a
`outputs/model-coordinator-job/` (el pid como texto, `pid.txt`), y el directorio se movió fuera
del árbol, al scratchpad de la sesión: sin eso, el gate rehúsa cualquier commit del clon.

### TASKs y claims

ES-C no posee ninguna fila en `.claude/coordination/claims.jsonl`: las 9 filas `vm-c` son de
VM C (`feature/vm-c-clean-room`, `session_01Gg7heFfxzA…`), otro nodo. ES-C no ejecutó ninguna
TASK de thyrox. Su trabajo de ai-course-notes:

| Lote | Estado | Escrito por | Árbol git del banco |
|---|---|---|---|
| 31 cs224n | preparado (165 fragmentos), 0 traducidos | `translation_loop.py prepare`, sin modelo | `54728afd` |
| 32 cs336 | preparado (250), 0 traducidos | ídem | `150f883a` |
| 33 cs336-2026 | preparado (210), 0 traducidos | ídem | `9a6f94d6` |

### Procesos, jobs y triggers

| Pieza | Estado | Instrumento |
|---|---|---|
| coordinador de modelos | `sin coordinador sano` (socket y candado del 2026-10-08, sin proceso) | `bin/model_coordinator status` |
| motor Podman | `KNOWN_POST_REBOOT_RECOVERABLE`; locks asignados 0, referenciados 2 | `bin/local_control_plane_ready --status` |
| `thyrox-ollama` | Podman lo declara `running` con pid 3535, que no existe tras el reinicio: estado obsoleto, no se tocó | `podman inspect` + `ps` |
| jobs propios | ninguno vivo | `ps` |
| triggers habilitados de esta cuenta que disparan aquí | 0 (el check-in propio se canceló el 2026-10-08) | `list_triggers` |

**Barrera de admisión.** thyrox no tiene una autoridad de barrera de suspensión (búsqueda:
`bin/` y `src/` por `suspend|quiesce|drain|pause|barrier|checkpoint|handoff|resume`; sólo
aparecen `drain_spool`, `resource_admission` y `session-resume`, éste DEPRECATED
H-THYROX-187, ninguno admite o veta asignaciones). En este nodo la admisión es nula de hecho:
sin coordinador, sin lazo y sin triggers. Riesgo residual: ES-A puede crear un trigger nuevo
hacia esta sesión.

### Imágenes Podman (`outputs/podman-images.tsv`)

Podman 4.9.3, overlay, sqlite, `/var/lib/containers/storage`. Volumen `thyrox-ollama-models`
(32 KiB, sin modelos). Sin pods.

| Imagen local | ID | Digest | Remoto (HEAD 02:09Z, anónimo y lector) | Clase |
|---|---|---|---|---|
| `th3rox/thyrox-task-runner` | `2bb9f235830e` | `sha256:1cced65c…` | 200 MATCH | reproducible por digest |
| `ollama/ollama` (= `th3rox/cache-ollama--ollama`) | `c178b43788bb` | `sha256:2a6e883b…` | 200 MATCH en los dos | reproducible por digest |
| `th3rox/cache-library--ubuntu` | `69f919497cad` | `sha256:a853f94d…` | 200 MATCH | reproducible por digest |

Las tres se trajeron por digest; ninguna se construyó aquí. **No hay nada que publicar.** No se
borró ninguna. *Ciega a:* la integridad de las capas remotas (HEAD de manifiesto, sin bajar).

### Modelos

Sin GGUF en el disco (`find / -xdev -name '*.gguf' -size +100M`: 0). El 9B es recuperable por
su artefacto OCI: `th3rox/kaupamex-ai-model-artifacts@sha256:54a969a7…` 200 MATCH y blob
`sha256:03b74727…` 200 (anónimo y lector). Sin cualificaciones nuevas de este nodo.

### Credenciales

`THYROX_REGISTRY_READER_USERNAME`/`_TOKEN` están en el entorno del nodo y obtienen token
(columna `reader`). No se imprimieron ni se versionan. `.env` de thyrox (identidad del commit,
rutas) está ignorado por git y se pierde con el nodo: se regenera con `write-env.sh` más
`THYROX_COMMIT_AUTHOR`/`_COMMITTER` de `.claude/rules/git.md`.

### Lo que desaparece con el nodo

Las tres imágenes y el volumen vacío (recuperables por digest), `.env`, `node_modules`,
`.venv` y los paquetes del toolchain (regenerables con el checklist). Nada exclusivo.

## Bloqueos que siguen abiertos

1. `local-models-ensure` → 429 *pull-rate* de Docker Hub (`outputs/local-models-ensure.json`):
   la IP de salida agotó 100 *pulls*/h. Con lector autenticado el límite es por cuenta; no se
   midió si `ensure` usa la credencial de lectura para traer imágenes.
2. Disco: 11 GB libres tras traer las imágenes; la cadena completa del 9B pide ≈20,8 GB
   (estimación de VM C). Un nodo nuevo con ≥ 21 GB libres es la condición.
3. `THYROX_REACH_ROOTS` sin declarar: `bin/declarations` y `check_githooks_activos` rehúsan.
4. ai-course-notes `0580f5a1` y `372c547a` con author por defecto del contenedor; reescribirlos
   pide *force-push*, rehusado por el clasificador de permisos.

## Reanudación de este nodo, si se reutiliza

1. `git -C thyrox ls-remote origin feature/es-mx-vm-c-local-worker` y lo mismo en
   ai-course-notes: tienen que coincidir con los HEAD de arriba o con sucesores.
2. Releer este registro y el banco `ai-course-notes:.claude/workbench/es-mx-vm-c-20261008T015924Z/RECORD.md`.
3. `bin/local_control_plane_ready --status` antes de cualquier arranque.
4. Reintentar `bin/local-models-ensure thyrox-unsloth--qwen3.5-9b-gguf:q4_k_m-hf-3885219b6810`
   sólo con disco suficiente y fuera de la ventana del 429; las imágenes ya están.
5. Sin re-preparar los lotes 31–33: ya están en git.

## Verificación

Se leyó de vuelta: los dos `ls-remote` tras el push, `git status` limpio salvo lo ignorado.
