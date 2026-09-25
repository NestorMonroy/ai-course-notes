# Ola 1: lotes 2 a 9 del plan

`translate_wave.sh --from 2 --to 9 --jobs 4 --compile`: 8 lotes de una nota,
4 a la vez con anchura 2 cada uno.

| Resultado | Lotes |
|---|---|
| limpio (exit 0) | `talks__20vc`, en 2 iteraciones |
| pide juicio (exit 3) | los otros 7, sin ensamblar tras la iteración 01 |

**Causa medida:** 18 de 93 ítems terminaron con `error_max_turns`. Con `Grep`
sobre `source.srt`, el modelo usa más turnos: 46 ítems usaron 2, 19 usaron 3,
10 usaron 4 y 18 agotaron el tope de 4 sin responder. Además, `advance` trataba
un lote sin ensamblar como un asunto de juicio y paraba tras un solo intento.

**Corregido en el commit siguiente:** tope de 8 turnos (cubre la cola medida),
la causa del rechazo en el mensaje (`rechazado (error_max_turns)`) y `advance`
reintenta los fragmentos pendientes en la vuelta siguiente. La ola se repite
sobre los mismos lotes.
