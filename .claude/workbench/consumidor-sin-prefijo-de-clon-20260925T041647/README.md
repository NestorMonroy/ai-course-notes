# Consumidor sin el prefijo de clon del proveedor

Primer consumidor de THYROX cuyo nombre de clon **no** lleva `kaupamex-`:
`ai-course-notes`. Rama `feature/ai-course-notes-l1`, creada desde
`feature/thyrox-l6@bacdb771`.

El banco vive en el CONSUMER, `ai-course-notes/.claude/workbench/`: el trabajo
que lo produjo es de este consumer, aunque los hallazgos sean sobre codigo de
THYROX. Se creo primero en `thyrox/.claude/workbench/` y se movio aqui; la
correccion de H-THYROX-179 y su suite siguen en la rama de THYROX, porque son
codigo del PROVIDER.

Reproducir, desde la raiz de ai-course-notes (la raiz de THYROX sale del `.env`
del consumer por `tools/thyrox/lib.sh`; todo ocurre bajo un `mktemp -d`):

```bash
bash .claude/workbench/consumidor-sin-prefijo-de-clon-*/probes/probe.sh
```

Salida registrada: `outputs/probe.out`.

| Hallazgo | Seccion de la sonda |
|---|---|
| H-THYROX-176 — la familia `THYROX_WORKBENCH_<CLONE>` ignora en silencio la clave de un clon sin prefijo | `## 1` |
| H-THYROX-177 — `root()` compone `<prefijo><repo>` aunque el clon no lo lleve, y `declarations.py` crea esos hogares fantasma, que despues confirman el roster | `## 2` |
| H-THYROX-178 — sin `start`, el `.env` se busca desde `src/paths/` de thyrox y no desde el cwd: `agent_store` invocado en un consumidor escribe en el store del proveedor | `## 3` |
| H-THYROX-179 — `THYROX_JOBS_DIR` nombra el ledger en `wait-jobs.sh` y el hogar de runs en `job_runs.py`; un consumer no podia llevar su ledger a su arbol. Corregido con `THYROX_JOBS_LEDGER_DIR` | `tests/session/test-wait-jobs-ledger-home.sh` |

## Donde viven los hallazgos

En este banco. Las cuatro filas se registraron primero en el store de THYROX
—un ejemplo del mecanismo, que no se llena desde este trabajo—, se retiraron
de ahi restaurandolo a `feature/thyrox-l6@bacdb771`, pasaron al store del
consumer y ese store se retiro despues por decision del ejecutor: este
consumer no tiene store de agentes. La tabla de arriba y `outputs/probe.out`
son el registro.

## Como se destapo el 177

Al inspeccionar el consumidor con `declarations.py` —que se presenta como
registro de lectura— aparecieron en el host `/home/user/kaupamex-ai-course-notes/`
y `/home/user/kaupamex-thyrox/`, vacios salvo `.claude/workbench/`. En la
invocacion siguiente, sin `THYROX_REACH_ROOTS`, el `ReachRootError` ya no
salia: el roster se derivaba de esos fantasmas. Se borraron (0 archivos) y la
sonda reproduce el ciclo bajo `THYROX_REACH_ROOT=$TMP/reach`.

*Metrica:* salida de `workbench_dir`, `repo_of`, `clone_suffix_of`,
`declarations.py` y `hallazgo_ids.py acunar`, y el `find` de lo que (b) creo.
*Ciega a:* los `.rst` de `kaupamex-docs`, que no estan en este contenedor: los
numeros 176 a 179 se acunaron contra las filas del store de THYROX (max 175), no contra el
corpus RST — el acunador mismo no corre aqui, por el 177.
