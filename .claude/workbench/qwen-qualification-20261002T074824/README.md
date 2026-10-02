# qwen-qualification

## El encargo

<!-- verbatim, sin parafrasear -->

> adelante con la cualificación de Qwen en TDD

## La premisa, si se corrigio al primer comando

thyrox no tenía cómo cualificar un modelo para una clase de tarea (lo añadió
TASK-THYROX-0780) y el pool pedía al recomendador 126 029 tokens de contexto
(lo corrigió TASK-THYROX-0781). Lo que toca a este proyecto: escribir su suite
con su trabajo real, declarar el contexto de sus ítems y su propio archivo de
cualificaciones.

## Las piezas

| archivo | que hace |
|---|---|
| `probes/qualification_suite.py` → `tools/scripts/qualification_suite.py` | casos con el prompt de `translate` (`build_prompt`) y el fragmento en el mensaje; exige `<<<ES`/`ES>>>`, cero chino, la estructura LaTeX que la referencia conservó y ninguna forma prohibida (mayúscula inicial incluida) |
| `probes/test_qualification_suite.py` → `tests/` | sus 7 pruebas |
| `probes/control.ts` | control discriminante con el puntuador de thyrox |
| `probes/context_red.py`, `probes/context_impl.py` | `translate --context-tokens 32768` y la clave `THYROX_MODEL_QUALIFICATIONS` en `tools/thyrox/README.md` |
| `probes/annul.py` | seis anulaciones del generador |

La suite: `tools/lang/es-mx/qualification/translation-suite.json`, 6 casos de
`cs329a` repartidos por tamaño (de 66 a 79 comprobaciones cada uno).

## Los resultados

| Paso | Resultado | Evidencia |
|---|---|---|
| generador: rojo / verde | módulo ausente / 7 de 7 | `outputs/red.txt`, `outputs/green.txt` |
| control | los 6 casos: la traducción aceptada aprueba; el chino y la traducción sin marcadores suspenden → discrimina | `outputs/control.txt` |
| contexto: rojo / verde | la prueba del pool falla / 68 de 68 (ciclo + suite) con la imagen del consumidor | `outputs/context-*.txt` |

| Anulación | Cae |
|---|---|
| sin excluir el chino | sólo la de marcadores y chino |
| exigir estructura que la referencia no conservó | sólo la de estructura |
| contar lo comentado como estructura | sólo la de estructura |
| sin mayúscula inicial | las dos de formas prohibidas |
| escapar como Python, no como JS `u` | las dos de formas prohibidas |
| elegir un fragmento sin referencia | sólo la de selección — tras endurecerla: la primera versión no caía, porque 3 de 7 no llegaban al fragmento sin referencia |

*Metrica:* pruebas en rojo, verde y bajo cada anulación; aprobado o suspendido de cada caso en el control.
*Ciega a:* la fidelidad del sentido: ninguna comprobación léxica la ve.
