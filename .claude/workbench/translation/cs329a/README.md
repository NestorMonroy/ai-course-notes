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
