# N VMs con modelos locales para la traducción es-MX — análisis del mecanismo

- Nodo que escribe: la sesión de ai-course-notes (`session_011tfzc28GV3swU7BCpC5uQr`),
  ramas `feature/es-mx-translation` (ai-course-notes) y `feature/ai-course-notes-l1` (thyrox).
- Fuente: `feature/fresh-clone-bootstrap` integrada en `feature/ai-course-notes-l1`
  (`8f9da7513`, `ddc729130`), y los bancos de VM B (`claude/vm-b-portability`) y VM C
  (`feature/vm-c-clean-room`).
- Fecha: 2026-10-08T01:50Z.

## Qué es una «VM» en ese mecanismo

Una VM es una **sesión remota de Claude Code**: un contenedor propio (4 vCPU, 16 GB,
disco propio, medido en VM B: 29 GB libres), un clon propio y **una rama propia cuyo
nombre dice su papel** (`claude/vm-b-portability`, `feature/vm-c-clean-room`). La VM A
coordina; las demás registran en su banco «Nodo: VM X · rama … · Coordinador: VM A
(session_…)». La comunicación es:

| Canal | Qué lleva |
|---|---|
| git (rama por VM, merges desde `feature/fresh-clone-bootstrap`) | código integrado y los registros (`RECORD.md`) |
| mensaje entre sesiones | la asignación de trabajo y su respuesta |
| registro OCI por digest (Docker Hub `th3rox/*`) | modelos e imágenes, nunca por copia entre VMs |

No hay estado compartido entre VMs fuera de esos tres canales: cada una tiene su
coordinador de modelos, su caché y sus PID. Por eso el PID versionado en `outputs/pid`
es un defecto N-VM (H-THYROX-575, TASK-THYROX-1037 en rojo): otra VM lo lee como suyo.

## Por qué escalar en horizontal y no con más ranuras en una VM

`scheduler-search-existing-20261008T002247/RECORD.md:45` (thyrox): **Qwen3.5 no sirve
peticiones paralelas** (Ollama las rehúsa; llama.cpp b11277 corrompe la salida). La
admisión fija la concurrencia de inferencia en 1 por residencia, y una VM de 16 GB sólo
admite una residencia del 9B. Esto corrige lo que se dijo antes en esta sesión sobre
`runtimeServing.ts` (N secuencias por residencia): la pieza existe, pero con este modelo
no da concurrencia. **Una VM = un 9B = una traducción a la vez**; N VMs = N a la vez.

## Ajuste a la traducción es-MX

El plan de traducción ya es un DAG sin aristas entre lotes: cada lote escribe sólo en su
directorio de notas y en su banco. Eso lo vuelve el caso ideal de carriles estáticos:

| Lote(s) | Estado medido 01:50Z | Carril |
|---|---|---|
| 26 kaist-cs492d | 22/164 fragmentos | VM A, llama-direct (9B) |
| 35 cs25 | 505/505 | terminado (Opus por el pool) |
| 34 youtube__zhangxiaojun | 311/445 | VM A, pool (Opus) |
| 27–33 | sin preparar | libres para VM B…N |

Recursos compartidos que hoy escriben varios lotes y necesitan un solo escritor:

- `tools/lang/es-mx/translation_memory.jsonl` — lo reescribe el barrido al final de cada
  ola (`translate_wave.sh:70`);
- `.claude/workbench/translation/batches.tsv` — registro de iteraciones;
- `.claude/workbench/.last-bank`.

En N VMs, cada trabajador corre sus olas sin barrido y el barrido lo hace sólo el
integrador sobre `feature/es-mx-translation`; si no, cada merge choca en esos archivos.

## Qué bloquea hoy un trabajador limpio con el 9B

Medido por VM C (`feature/vm-c-clean-room`, Fase 1) y válido para cualquier VM nueva:

| Pieza | Estado |
|---|---|
| artefacto OCI del 9B `th3rox/kaupamex-ai-model-artifacts@sha256:54a969a7…` | 200 anónimo; el blob `sha256:03b74727…` también: **1031 no bloquea** |
| `bin/local-models-ensure` | ruta productiva, pero exige la imagen verificadora ya local → **TASK-THYROX-1032** |
| `thyrox-ollama` | arranca por etiqueta `ollama:0.35.0` → **TASK-THYROX-0944** |
| imagen task-runner por digest | `createImageResolver` existe sin consumidor → EXTEND (H-THYROX-574) |

El carril llama-direct de este nodo usa el GGUF que ya está en su caché y la imagen de
Ollama ya presente; **una VM nueva no tiene ninguno de los dos**, y traerlos sin las
autoridades (copia del GGUF, `pull` por etiqueta) es justo lo que la regla de identidad
inmutable prohíbe. Hasta que 1032 y 0944 se integren, una VM nueva de traducción puede
hacer sólo trabajo determinista (bootstrap, verificación por digest, preparar lotes) o
traducir por el pool con un modelo remoto.

## Nombres propuestos (por mecanismo, como `vm-b-portability` / `vm-c-clean-room`)

| VM | Papel | thyrox | ai-course-notes |
|---|---|---|---|
| ES-A (este nodo) | coordinador + carril llama-direct | `feature/ai-course-notes-l1` | `feature/es-mx-translation` (integración) |
| ES-B | trabajador local, lotes 27–30 | `feature/es-mx-vm-b-local-worker` | `feature/es-mx-vm-b-local-worker` |
| ES-C | trabajador local, lotes 31–33 | `feature/es-mx-vm-c-local-worker` | `feature/es-mx-vm-c-local-worker` |

Cada trabajador integra su rama en `feature/es-mx-translation`; ninguno escribe en la
rama de otro.

## Ciega a

- No se midió una VM nueva de esta sesión: la tabla de bloqueos es la de VM C.
- No se midió el rendimiento real de dos VMs traduciendo a la vez.

## Imágenes y modelo en Docker Hub (verificado 01:44Z, `outputs/manifest-head.tsv`)

HEAD de manifiesto por digest con `probes/manifest-head.sh` (copiado de VM C): las seis
piezas que un trabajador necesita responden **200 anónimo con el digest pedido**
(REMOTE_VERIFIED): espejos `th3rox/cache-pgvector--pgvector`, `cache-library--redis`,
`cache-ollama--ollama` (`sha256:2a6e883b…`, el mismo digest que la imagen de Ollama de
este nodo), `cache-library--ubuntu`, la imagen `th3rox/thyrox-task-runner@sha256:1cced65c…`
y el artefacto del 9B (manifiesto `sha256:54a969a7…` y blob `sha256:03b74727…`). No hay
nada que publicar antes de crear ES-B y ES-C.

## Carriles al crear ES-B y ES-C

ES-A limita sus lazos: llama-direct sólo el lote 26 (`llama_direct_ensure.sh --to`),
Opus por el pool sólo el 34. Lotes 27–30 → ES-B, 31–33 → ES-C.
