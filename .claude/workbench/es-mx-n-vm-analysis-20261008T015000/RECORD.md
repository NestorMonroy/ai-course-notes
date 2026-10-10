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

## VMs creadas (2026-10-08T01:47Z)

| VM | Sesión | Rama (ai-course-notes y thyrox) | Lotes | Prompt |
|---|---|---|---|---|
| ES-A | `session_011tfzc28GV3swU7BCpC5uQr` | `feature/es-mx-translation` · `feature/ai-course-notes-l1` | 26 (llama-direct), 34 (Opus) | — |
| ES-B | `session_016p3UBXf4mRLCtP2rC41jKy` | `feature/es-mx-vm-b-local-worker` | 27–30 | `prompts/es-b.md` |
| ES-C | `session_019WeSB4iBHjpqYB9as4SQBH` | `feature/es-mx-vm-c-local-worker` | 31–33 | `prompts/es-c.md` |

Las dos parten de `4822fd5` (ai-course-notes) y `ddc729130` (thyrox). La plantilla
común es `prompts/worker-template.md` (`__VM__`, `__vm__`, `__LOTES__`); una VM nueva se
crea con ella, su propia rama `feature/es-mx-vm-<x>-local-worker` y lotes disjuntos.

## Prueba local de ES-A (2026-10-08T06:4xZ, `outputs/proof-es-a-kaist-cs492d.tsv`)

`tools/scripts/llama_direct_proof.sh <lote>` extiende la cadena de
`vm-utilization-audit-*/probes/local-proof.sh` (thyrox) al carril llama-direct, que no pasa
por el coordinador: SHA del blob GGUF montado = catálogo → contenedor del carril con la
imagen de Ollama por digest → modelo residente en `/api/ps` → `model` de cada resultado
del runner = el pedido, runtime `llama-direct` → ningún modelo remoto. Resultado en el
lote 26: **`LOCAL_WORKER PROVEN`**.

Ciega a: de las 142 respuestas del último `translate/`, la mayoría son reutilizadas de
ejecuciones anteriores del mismo carril (`reused_from`); la prueba confirma su
procedencia llama-direct, no que se hayan generado en esta ejecución.

Lo que destapó al escribirla (H-THYROX-642): tras el reinicio de las 06:22 había siete
contenedores de Ollama de arranques anteriores; `reconcile-orphans` retiró cuatro y
también el servidor vivo, y dejó dos huérfanos con imagen por etiqueta montando el mismo
blob. La primera versión de la prueba eligió uno de ellos y falló cerrada.

## ES-B y ES-C (06:2xZ)

Integradas en `feature/es-mx-translation` (`9fd582a5`, `632a26a6`): prepararon sus lotes
sin modelo. Siguen `BLOCKED`: sus sesiones no pueden adjuntar thyrox (`add_repo` y
`git clone` rechazados por el clasificador de permisos). Requiere aprobación de la persona
en cada sesión o recrearlas con thyrox como segunda fuente.

## Corrección: el primer PROVEN era falso (07:2xZ)

La versión de 06:4xZ contaba como respuesta todo `<n>.json` con `runtime: llama-direct`.
Las 142 «respuestas» de `translate/20261008T062530/` eran errores `Connection refused`:
el runner falló el lote entero en un segundo cuando `reconcile-orphans` retiró el
servidor (H-THYROX-642). La prueba ahora sólo cuenta resultados sin `subtype` de error y
con el fragmento entre marcadores, informa `errors=N`, y elige la última ejecución con al
menos una respuesta real. Con eso, el lote 26 da `LOCAL_WORKER PROVEN` sobre **3
traducciones reales** (`outputs/proof-es-a-kaist-cs492d.tsv`), no 142. Ritmo medido en
la ejecución en curso: 339–1171 s por fragmento; 142 pendientes.

## Segunda corrección: «3 traducciones reales» tampoco era cierto (17:5xZ)

La prueba de 07:2xZ miraba sólo la apertura `<<<ES`; el lazo exige además el cierre
`ES>>>` (`translation_loop.extract_translation`) y la misma estructura de entornos
(`structure_problem`). Medido sobre `translate/20261008T062556/`: las 6 respuestas con
`done_reason` stop **abrían bien y cerraban con la cerca ```` del mensaje** en vez de
`ES>>>`, porque `build_message` incrusta el fragmento en una cerca ````latex. El lazo
rechazó las 6 y `recover_pool_results` escribió 0. El PROVEN anterior contaba respuestas
que el lazo no acepta.

Corrección:

- `llama_direct_runner.close_markers`: si la respuesta abre `<<<ES` y no tiene `ES>>>`,
  quita la cerca final y cierra. Se aplica a la respuesta nueva y a la reutilizada; el
  mensaje además dice que la última línea es `ES>>>`.
- `recover_pool_results` la aplica a los resultados `runtime: llama-direct` anteriores.
  Ejecutado: 10 fragmentos escritos del lote 26 (lecture01 001–003, 005; lecture02
  004, 006–008 y `head`; lecture03 `head`), ninguno con `ctex`.
- `llama_direct_proof.sh` cuenta como real sólo lo que acepta el mismo
  `extract_translation` + `structure_problem` del lazo.

Resultado (`outputs/proof-es-a-kaist-cs492d.tsv`): `LOCAL_WORKER PROVEN`,
`qwen35-9b-es-mx×6 (responses=6, errors=0)`, sin modelo remoto.

Ciega a: el lazo en curso (desde 17:48Z) arrancó con el runner anterior en memoria y
vuelve a pedir esos fragmentos; sus respuestas quedan en `<n>.json` y la siguiente
vuelta las reutiliza ya cerradas, así que el costo es tiempo, no trabajo perdido.

## Auditoría y consolidación de ES-B y ES-C (17:5xZ)

Pedida por el ejecutor: si no trabajaban con modelos locales, que entregaran su trabajo
para consolidarlo aquí. Las dos entregaron (`75b59c93` ES-B, `b1061513` ES-C) con su
sección «Auditoría y entrega».

| VM | Modelo que escribió | Estado | Causa medida | Entrega |
|---|---|---|---|---|
| ES-B | ninguno | `NOT_PROVEN sin acceso a thyrox` | el clasificador rehusó `add_repo`/`clone` de thyrox | preparación determinista de 28 articles (258 fragmentos), 29 berkeley f25 (213), 30 cs231n (171) |
| ES-C | ninguno | `NOT_PROVEN docker-hub-429-pull-rate` | thyrox sí; `local-models-ensure` falló con 429 de Docker Hub | preparación determinista de 31 cs224n (165), 32 cs336 (250), 33 cs336-2026 (210); merge de fresh-clone-bootstrap en su rama de thyrox (`2156f9cc2`) |

Ninguna escribió un fragmento con un modelo remoto: 0 `<n>.json` y 0 `*.es.tex` nuevos en
sus lotes. El lote 27 cs25-v6 sólo tiene `000.es.tex` de portada (copia de `prepare`) y dos
respuestas llama-direct de ES-A del 2026-10-07.

Defecto heredado: `0580f5a1`, `372c547a` (ES-C) y `93bfc7f8`, `1b65eb85`, `75b59c93` (ES-B)
llevan la identidad por defecto del contenedor, no la de `.claude/rules/git.md` (thyrox).
Reescribirlos exige reescribir la historia publicada de sus ramas; se deja así y se
declara aquí.

Con eso, los lotes 27–33 siguen sin traducir y el único carril local que traduce es el de
ES-A (lote 26). Una VM trabajadora queda útil sólo con acceso a thyrox y el 9B traído sin
429 (autenticación de Docker Hub o espejo).

## Lote 26 asentado; ES-A toma los lotes 27–33 con el 9B local (2026-10-09T19:39Z)

- Lote 26 kaist-cs492d: 164/164 fragmentos traducidos por `qwen35-9b-es-mx`, 15/15 notas
  ensambladas. Salió `Exitval 3` (tope de 4 iteraciones con señales abiertas: 37 filas en
  `triage.tsv` que piden juicio, no otra vuelta del modelo) y quedó asentado en
  `.claude/cache/ola/llama-direct.settled`, que impide relanzarlo cada cinco minutos.
- Lotes 27–33 (1372 fragmentos, preparados por ES-B y ES-C sin modelo): los toma este
  carril, sólo con el modelo local. `llama_direct_ensure.sh` cambia su tramo por defecto a
  27–33 para que un reinicio de la VM lo relance ahí. Ningún carril remoto vivo (medido:
  0 procesos de `pool_proxy` o `headless-pool`).

## El carril pasa a llama-server, configurado por la ficha Qwen3.5-9B (2026-10-10T06:2xZ)

Integrada `feature/fresh-clone-bootstrap` en thyrox (`42f9e1729`). Conflicto en el store:
`H-THYROX-599` existía con dos hallazgos distintos (el nuestro de los huérfanos de
Ollama y el de `declaredCapabilitiesOf` de model-eval-campaign); el de la base conserva el
número y el nuestro pasa a **H-THYROX-642** (forma de H-THYROX-26).

Por qué Ollama hasta hoy: thyrox no ofrecía la unidad `llama-server` (runtime de GGUF =
Ollama, `RUNTIME_BY_FORMAT`) y faltaba lo que VM U midió para arrancarla
(`LD_LIBRARY_PATH=/app`, H-THYROX-639). Medido antes de cambiar: en 203 respuestas de
Ollama la mediana es 3.78 caracteres por token de salida (mínimo 2.7): sin razonamiento
oculto. Ciega a: un razonamiento corto mezclado con una salida larga.

Configuración frente a la ficha (`Qwen3.5-9B.txt` subida por el ejecutor):

| Ficha | Qué exige | En la unidad |
|---|---|---|
| l.162, l.400, l.436 | piensa por defecto; sin `/nothink`; se apaga con `chat_template_kwargs` | `--jinja --chat-template-kwargs '{"enable_thinking":false}'` |
| l.282 = l.581 | no-thinking general: 0.7/0.8/20/0.0, presence 1.5, repetition 1.0 | flags del servidor; `/props` lo confirma |
| l.585 | salida 32 768 | `-n 32768`, `-c 40960` |
| l.172 | ≥ 128K para preservar el thinking | no aplica: thinking apagado; 128K no cabe en la unidad de 9 GiB (W §4) |
| l.584 | presence alto puede mezclar idiomas | se mantiene 1.5; vigilar `prose:english` y `parity:residual-han` |
| l.198, l.530 | MTP, YaRN | el GGUF no trae `nextn`; contexto < 262 144 |

Lo que la medición corrigió: `/props` daba `reasoning_format: none`, así que un `<think>`
habría llegado en `content` y `thinking_chars` habría marcado 0 sin poder verlo. Ahora
`--reasoning-format deepseek` lo separa a `reasoning_content`, y el runner cuenta además
cualquier `<think>` que llegue en el texto.

Por qué `thinking_chars` debe ser 0: la traducción es una tarea general (perfil l.282), en
CPU cada token de razonamiento cuesta lo mismo que uno de salida (~3 tok/s), y el thinking
pide ≥ 128K de contexto (l.172), que esta unidad no admite. 0 es la prueba de que la
configuración del servidor se aplicó, no un supuesto.
