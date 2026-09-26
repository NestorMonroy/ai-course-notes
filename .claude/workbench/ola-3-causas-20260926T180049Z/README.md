# Ola 3: siete causas compartidas, separadas y decididas una a la vez

## Separar antes de decidir

Leídos sus contextos, tres «causas compartidas» no lo eran, o no del todo:

- `parity:residual-han` juntaba cinco notas: dos comparten el nombre del
  programa («Ungrounded 不着边际»), las demás son restos locales distintos.
  `cause_key` ahora agrupa por la primera secuencia Han del detalle.
- `compile:missing-glyph:han`: «珺» (U+73FA) no está en FandolSong. El
  preámbulo es-MX carga xeCJK con AutoFallBack y WenQuanYi Zen Hei de
  respaldo; la compilación de prueba dio 0 caracteres faltantes.
- `compile:missing-glyph:U+FFFD`: el modelo partió caracteres multibyte
  («est��», «qu��»). Un fragmento que trae U+FFFD y su original no, se rechaza
  al llegar.

Y `sweep` recorría sólo `*-notes.es-mx.tex`: el respaldo CJK no llegó a cuatro
preámbulos compartidos ni a dos plantillas, que `measure` sí verifica. Ahora
los dos usan el mismo recorrido; el barrido real dejó 0 archivos sin respaldo.

## Decisiones medidas (`decisions.tsv`)

| Decisión | Neto |
|---|---|
| olas 2 y 3 (lo que cambiaron desde la medición anterior) | −30 |
| glosario: commit y full-stack se conservan | +4 |
| glosario: auditability → capacidad de auditoría | −4 (ver abajo) |
| xeCJK con respaldo | 0 (`measure` sin `--compile` no ve esta señal) |
| U+FFFD, dos casos exactos | 0 (ídem) |
| Ungrounded (不着边际) | +2 |
| «correr el», dos casos exactos | +2 |

El −4 de auditability no es un retroceso del texto: una fila de glosario no
cambia la nota hasta retraducir, y mientras tanto la palabra sale como inventada
y como rechazada. El PLAN dice ahora que una decisión de glosario se mide
después de su retraducción.

## TDD y anulación

- `red.txt`, `red-sweep.txt`: las cuatro mitades en rojo.
- `annul-summary.txt`: Q1 (sin respaldo CJK), Q2 (sin rechazo de U+FFFD), Q3
  (sin clave de residuo Han) y Q4 (barrido sólo de `*-notes`) hacen caer cada
  una exactamente su prueba.
- Q2 no casó la primera vez: la cadena `�` escrita en el comando llegó
  convertida al carácter U+FFFD real antes de ejecutarse (bytes 357 277 275).
  Se repitió construyendo la barra con `printf '\x5c'`.
