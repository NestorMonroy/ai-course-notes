# El límite de la cuenta detiene la ola, no se reintenta

## El episodio (ola 2)

cs146s e interviews__zhang-xiaojun retradujeron 7 y 21 fragmentos en cada
iteración sin ensamblar nunca. Los `N.json` del pool dicen por qué: 105 de 117
rechazos eran `"You've hit your session limit · resets 4am (UTC)"`, con
`subtype: success` y sin marcadores. `advance` los tomó por fragmentos
rechazados y los reintentó hasta el tope. Los fragmentos aceptados sí quedaron
en el banco (`NNN.es.tex`: 61 de 66 y 22 de 43) y se reutilizan.

## TDD

- `red-limite.txt`: `advance` volvía a llamar al modelo.
- `red-ola.txt`: los tres lotes de la ola llamaban al modelo.
- `annul-summary.txt`: L1 (translate no detecta), L2 (cycle ignora el 5) y L3
  (advance reintenta) hacen caer las dos pruebas del límite, porque la de la
  ola depende de que advance devuelva 5; L4 (la ola sin marca) sólo la de la
  ola. Las demás pasan en las cuatro.

## Por qué se consumieron los tokens

Medido en el transcript de la sesión y en todos los `usage.tsv`: la
conversación que orquesta leyó 1,152,885,383 tokens de caché en 2,904
respuestas (~397,000 por respuesta); el pool, 18,296,741 en 696 fragmentos
(~26,000). El detalle y las reglas de operación que salen de ahí están en la
sección 9.1 del PLAN.
