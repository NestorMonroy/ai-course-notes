# tools/thyrox — ai-course-notes como CONSUMER de THYROX

THYROX es el PROVIDER: aporta los mecanismos (store de agentes, trabajos en
segundo plano, gates). Este directorio **no copia** ninguno. Contiene solo los
wrappers que preparan el entorno del consumer y delegan en
`$THYROX_ROOT/bin/`. Una copia divergiria en silencio del original; el gate
`check_consumer_copies` de THYROX existe por ese defecto.

## Precondiciones

1. THYROX clonado y con su entorno generado (`cd "$THYROX_ROOT" && uv sync`).
2. Un `.env` en la raiz de este repositorio, excluido de git por `*.env`. Como
   minimo declara `THYROX_ROOT`; el resto de las claves y su significado estan
   en `$THYROX_ROOT/.env.example`. El que usa este consumer:

   | Clave | Valor en este consumer |
   |---|---|
   | `THYROX_ROOT` | la raiz del clon de THYROX |
   | `THYROX_CONSUMER` | la raiz de este repositorio |
   | `THYROX_WORKBENCH_DIR` | `<consumer>/.claude/workbench` |
   | `THYROX_BACKGROUND_LOG_DIR` | `<consumer>/.claude/build-logs` |
   | `THYROX_JOBS_DIR` | `<consumer>/.claude/jobs` |
   | `THYROX_JOBS_LEDGER_DIR` | `<consumer>/.claude/jobs-ledger` (cada sesion recibe su subdirectorio) |
   | `THYROX_TOOLCHAIN_AWK_BIN` | `gawk` |
   | `THYROX_COMMIT_AUTHOR` / `THYROX_COMMIT_COMMITTER` | la identidad de los commits |

Sin el `.env`, los wrappers se niegan con codigo 2 en vez de continuar: THYROX
resolveria cada clave desde su propio `.env` y el store, los logs y el
workbench serian los del PROVIDER.

## Sin store de agentes

Este consumer no tiene store de agentes. `tools/thyrox/run` niega
`agent_store`, `task_ids` y `hallazgo_ids` mientras el `.env` no declare
`THYROX_AGENT_STORE`: sin esa clave, esos comandos leerian o escribirian el
store de THYROX (H-THYROX-178), que es un ejemplo del mecanismo y no se llena
desde aqui. Declararla los habilita contra el store que nombre.

## Comandos

```bash
tools/thyrox/run --print-env              # el entorno que se exporta
tools/thyrox/run --list                   # los comandos de $THYROX_ROOT/bin
tools/thyrox/run thyrox-bg start <n> -- <comando>
tools/thyrox/run check-toolchain-ready
eval "$(tools/thyrox/run commit_identity env)"   # identidad antes de commitear
tools/thyrox/check-prose-vocabulary       # la prosa en espanol nueva o modificada
```

## Por que existe cada pieza

| Pieza | Sin ella |
|---|---|
| `THYROX_ENV_FILE` exportada | un comando de `bin/` busca el `.env` desde su ubicacion dentro de THYROX y no desde el consumer: `agent_store` escribe en el store del PROVIDER (H-THYROX-178). |
| rechazo de `agent_store`, `task_ids` y `hallazgo_ids` sin `THYROX_AGENT_STORE` | caerian al store de THYROX (H-THYROX-178); `--repo` tampoco sirve, porque compone `<prefijo><repo>` y este clon no lleva el prefijo `kaupamex-` (H-THYROX-177). |
| `THYROX_WORKBENCH_DIR` global en el `.env` | la clave por clon `THYROX_WORKBENCH_AI_COURSE_NOTES` se ignora sin aviso (H-THYROX-176). |
| `THYROX_JOBS_LEDGER_DIR` en el `.env` | el ledger de `wait-jobs`, `run-task-pool` y `thyrox-bg register` cae en `<thyrox>/.claude/jobs-ledger/`. `THYROX_JOBS_DIR` no sirve para eso: en `job_runs.py` nombra el hogar de los runs (H-THYROX-179). |
| `VOCAB_GATE_*` exportadas | el gate de vocabulario solo lee sus parametros del proceso, no del `.env`. |

## El gate de vocabulario: que mide y que no

`check-prose-vocabulary` invoca `check_vocabulario_prosa` de THYROX con
`--strict` y con `prose_vocabulary_baseline.txt`, vacio porque la prosa en
espanol de este consumer empieza sin deuda. Mide dos ejes:

- **palabra inventada**: una palabra con sufijo nominal del espanol (`-cion`,
  `-dad`, `-miento`, `-anza`, `-encia`) ausente del lexico
  `spacy-lookups-data` (1 000 000 de formas);
- **forma prohibida**: la lista de THYROX `vocabulario_prohibido.txt`
  (clichés, coloquialismos y falsos amigos, como traducir *library* por su
  parecido gráfico en vez de por su significado).

Opera sobre el **significante** —la forma escrita— y no alcanza el
**significado**. Por eso no ve, y un resultado sin hallazgos no lo descarta:

| No detecta | Ejemplo |
|---|---|
| spanglish sin sufijo nominal | `deployeo`, `testear` |
| el registro regional: el lexico es panhispanico | `ordenador` pasa igual que `computadora` |
| si un termino tecnico debio quedarse en ingles | `andamiaje` por `scaffolding` |
| un falso amigo que no este en la lista | `eventualmente` por *eventually* |

Esos casos quedan a la revision de quien escribe y a un glosario de
terminos del consumer. Ampliar la lista prohibida desde aqui hoy no es
posible sin copiarla entera: `VOCAB_GATE_FORBIDDEN` la reemplaza, no la
extiende.

## Pruebas

```bash
pytest -q tests/test_thyrox_tools.py
```

Cada prueba copia este directorio a un consumer temporal; ninguna escribe en
el repositorio ni en el store de THYROX.
