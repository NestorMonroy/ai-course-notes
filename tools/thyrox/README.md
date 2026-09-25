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
   | `THYROX_TOOLCHAIN_TEXLIVE_PACKAGES` | los paquetes de TeX Live que piden las notas (XeLaTeX, español, TikZ, fuentes) |
   | `THYROX_TOOLCHAIN_TEXLIVE_PROBE_FILE` | `tools/templates/notes-template.es-mx.tex`: si compila, el entorno sirve para las notas |
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
tools/thyrox/run check-toolchain-ready    # incluye poppler y TeX Live (compila la plantilla es-MX)
THYROX_INSTALL_TEXLIVE=1 THYROX_INSTALL_POPPLER=1 tools/thyrox/run check-toolchain-ready   # y los instala si faltan
eval "$(tools/thyrox/run commit_identity env)"   # identidad antes de commitear
```

## Por que existe cada pieza

| Pieza | Sin ella |
|---|---|
| `THYROX_ENV_FILE` exportada | un comando de `bin/` busca el `.env` desde su ubicacion dentro de THYROX y no desde el consumer: `agent_store` escribe en el store del PROVIDER (H-THYROX-178). |
| rechazo de `agent_store`, `task_ids` y `hallazgo_ids` sin `THYROX_AGENT_STORE` | caerian al store de THYROX (H-THYROX-178); `--repo` tampoco sirve, porque compone `<prefijo><repo>` y este clon no lleva el prefijo `kaupamex-` (H-THYROX-177). |
| `THYROX_WORKBENCH_DIR` global en el `.env` | la clave por clon `THYROX_WORKBENCH_AI_COURSE_NOTES` se ignora sin aviso (H-THYROX-176). |
| `THYROX_JOBS_LEDGER_DIR` en el `.env` | el ledger de `wait-jobs`, `run-task-pool` y `thyrox-bg register` cae en `<thyrox>/.claude/jobs-ledger/`. `THYROX_JOBS_DIR` no sirve para eso: en `job_runs.py` nombra el hogar de los runs (H-THYROX-179). |
| claves `THYROX_TOOLCHAIN_*` y `THYROX_INSTALL_*` del `.env` exportadas | `src/lib/toolchain.sh` las lee solo del entorno del proceso: sin exportarlas, el preflight omitiria la sonda de TeX aunque el consumer la declare. |

## El gate de vocabulario ya no pasa por aquí

La revisión de la prosa en español es propia de este repositorio:
`tools/scripts/check_prose_vocabulary.py`, con sus datos en
`tools/lang/es-mx/`. Se copió y adaptó de THYROX para no depender de él; la
procedencia está en `tools/lang/es-mx/PROVENANCE.md`.

## Pruebas

```bash
pytest -q tests/test_thyrox_tools.py
```

Cada prueba copia este directorio a un consumer temporal; ninguna escribe en
el repositorio ni en el store de THYROX.
