# Lote cs329a (fase 2 del plan)

Banco estable del lote: cada `translation_loop.py cycle --batch cs329a` escribe
su iteración en `iterations/NN/` y una fila en `../batches.tsv`.

**Semilla:** los fragmentos es-MX de la primera pasada
(`../../fase2-cs329a-20260925T064016/`, 75 traducidos con la plantilla
anterior) se copiaron aquí para no volver a pagarlos. La iteración 01 los
verifica con el verificador corregido, y `retranslate` devuelve a pendientes
solo los que llevan señal.

## Iteración 02: veredicto falso de 0 señales

`batches.tsv` registra la iteración 02 con 0 señales, y **es falso**. La misma
lecture02, verificada de nuevo con el código estable, da 4 señales
(`iterations/02/reverificacion-lecture02.jsonl`): `\enquote`, «la clave está
en», `greedy` e `interpretabilidad`. Causa: un `verify-one` murió (con toda
probabilidad cargó `translation_loop.py` mientras se editaba) y `run_verify`
leyó «sin filas» como «sin señales». Se corrigió en el commit siguiente: cada
nota sin veredicto es una señal `verify:incomplete` y la verificación sale con
2. El registro es de solo agregar, así que la fila no se reescribe; la
iteración 03 registra el estado real.

## Lecture01 se une al lote

`plan` define el lote cs329a como el curso entero (9 notas). La lecture01 se
tradujo en el piloto (`../../piloto-traduccion-cs329a-lecture01-20260925T062301/`);
sus fragmentos es-MX se copiaron aquí como semilla, igual que los de la fase 2,
y desde la iteración 07 el lote verifica las 9 notas.

## Cierre del lote

| Iteración | Traducidos | Señales | Qué pasó |
|---|---:|---:|---|
| 01 | 0 (semilla) | 23 | el verificador corregido quitó 13 de las 36 de la primera pasada |
| 02 | 13 | 0 (**falso**) | un `verify-one` murió; ver arriba |
| 03 | 0 | 8 | veredicto real con el verificador arreglado |
| 04 | 6 | 6 | un fragmento volvió con `itemize` roto: V0 lo rechaza desde entonces |
| 05 | 5 | 3 | glosario (`batch`, `pool`, `factual`) y lista entera de formas prohibidas en la plantilla |
| 06 | 0 | 0 | ruta 1 (barrido de `（`, `）` y el cliché) y ruta 2 (`singulars`) |
| 07 | 0 | 0 | las 9 notas, con el título del curso fijo en `phrases.tsv` |

- **GATE A**: 18 entradas válidas y toda señal de las 7 iteraciones tiene su
  patrón. Una entrada preventiva que nunca se aplicó se retiró, porque el gate
  no acepta patrones sin evidencia.
- **GATE B**: iteraciones 5 y 6, con todos los patrones barridos.
- **GATE C**: 0 señales y revisión visual (`review.jsonl`) de lecture01, 02 y
  07; todas compilan sin errores ni glifos faltantes.
- **`report`** (`iterations.jsonl`, medido del banco y del historial de la
  memoria): 7 iteraciones, 18 notas con señal, 15 entradas de memoria, razón
  0.39. No es modo reactivo.

La revisión visual encontró lo que ningún verificador veía: el mismo título,
traducido de cinco formas. Es una causa compartida (ruta 2), resuelta una vez
en `phrases.tsv`.
