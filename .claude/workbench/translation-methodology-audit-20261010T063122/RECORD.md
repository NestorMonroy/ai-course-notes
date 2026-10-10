# Auditoría de la metodología y del procedimiento de traducción es-MX

- Nodo coordinador: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`); ai-course-notes
  `feature/es-mx-translation`, thyrox `feature/ai-course-notes-l1`.
- Encargo: `prompts/audit-spec.md` (literal, con la precisión del ejecutor: aplica a todo lo
  hecho, con el PROVIDER de thyrox como ejemplo, y se ejecuta con un modelo local con el
  razonamiento encendido en una VM nueva).
- Ejecutor de la auditoría: VM ES-D (`prompts/vm-d.md`), rama
  `feature/es-mx-vm-d-local-thinking-audit` en los dos repos.

## Fase 0 en ES-A (06:31Z, `probes/phase0.sh` → `outputs/`)

| Hecho | Evidencia |
|---|---|
| ai-course-notes `0e619951`, thyrox `acce34bc2`, ramas al día con su remoto | `outputs/git.txt` |
| 4 vCPU; RAM disponible 2.5 GiB de 15.7; disco con 2.3 GB libres (94 %) | `outputs/resources.txt` |
| 11 contenedores: 7 de Ollama con el dueño del carril (6 huérfanos de arranques anteriores, H-THYROX-642), 1 `llama-server`, 3 de `infrastructure-bootstrap` | `outputs/containers.json` |
| coordinador de modelos sin responder | `outputs/coordinator.txt` |
| plan: 4203 fragmentos, 2890 traducidos; 27 cs25-v6 59/105; 28–33 sin traducir | `outputs/progress.tsv` |

Capacidad en thyrox, medida en el árbol integrado (`42f9e1729`):

| Capacidad | Estado | Evidencia |
|---|---|---|
| unidad `llama-server` del coordinador | declarada, sin implementar | `src/packages/local-models/llamaServerUnitProfile.ts` lanza «pendiente: TASK-THYROX-1027» |
| runtime de GGUF del coordinador | implementado: Ollama | `hostCoordinatorComposition.ts` `RUNTIME_BY_FORMAT` |
| endpoint OpenAI-compatible declarado por entorno | retirado (M8) | `src/packages/provider/bin/localProxy.ts` `RETIRED_DECLARATION_NAMES` |
| modelo local alcanzado por admisión del coordinador | implementado | `localProxy.ts` `--local-model`, `headless-pool --local-only` |

## Consolidación del nodo antes de la auditoría (06:32Z)

Con 2.5 GiB disponibles no cabía un segundo servidor. El carril de Ollama se detuvo por la
autoridad del ledger (`wait-jobs adopt` del lazo y del grupo de `parallel`, `wait-jobs kill`), el
modelo se descargó por la API de Ollama (`keep_alive: 0`), y la unidad `llama-server` vieja se
retiró con `thyrox-bg register` + `wait-jobs kill`. Disponible tras eso: 15 GiB. `ensure` relanzó
`llama-server` (`-c 40960`, `-n 32768`, `--reasoning-format deepseek`) y el lazo 27–33 sobre él.

`/props` informa `reasoning_format: none` aunque el argv lleva `--reasoning-format deepseek`: el
campo es el valor por petición del slot, no el del servidor, y no se usa como evidencia; la
prueba del thinking apagado es `thinking_chars` en cada respuesta, que suma `reasoning_content`
y cualquier `<think>` llegado en el texto.
