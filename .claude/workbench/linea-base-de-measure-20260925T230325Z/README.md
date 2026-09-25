# La línea base de `measure`, y un falso positivo en los preámbulos

## El episodio

Primera decisión medida con `measure` (plan 2.1, ruta 2):
`internalize → interiorizar` en `self-evolving-agents-2026`. Resultado:
**0 resueltas, 6 introducidas, neto −6, salida 4.** Leído contra las filas:

- `internalizar` ya no aparece: la decisión sí resolvió su señal.
- La línea base valía 0. Sin medición anterior, `measure` comparaba contra
  la última iteración de cada lote, y la iteración 06 de este lote quedó
  «sin-ensamblar» (un fragmento rechazado), con `signals.jsonl` vacío.
- 5 de las 6 «introducidas» son `prose:english:variant` en los preámbulos
  compartidos. Ninguna iteración los verifica, y `measure` verifica todo
  `*.es-mx.tex`: ya estaban ahí antes de la decisión.

Es la advertencia de la 3.0.0 aplicada al instrumento: dos conjuntos que no
miden lo mismo. La fila −6 de `decisions.tsv` se conserva (solo se agrega).

## Correcciones, en TDD

1. **La primera medición es la línea base, sin neto.** `red.txt`; anulación
   I (restituir el respaldo contra la iteración) hace caer sólo la aserción
   de la línea base; C (comparar siempre contra la iteración) sólo la del
   caso sin cambios. 47 pasan en las dos (`annul-summary.txt`).
2. **`variant=mexican` no es prosa.** Un preámbulo compartido no tiene
   `\begin{document}` y se lee entero. En el lote, el zh hereda las
   palabras de código (`black`, `breakable`…); `variant` la agrega
   `localize` y no está en el zh, por eso sólo esa sobrevivía. Los nombres de
   paquete, clase e idioma (`\usepackage`, `\setdefaultlanguage`, …) se
   blanquean con su opción. `red-keyval.txt`; anulación P hace caer sólo
   `variant` (20 pasan).

Descartado en el camino: un patrón genérico `[clave=valor]`. Con los comandos
de la lista ya en blanco, ninguna prueba ni ningún caso del corpus lo
ejercitaba, y un patrón sin caso no tiene anulación que discrimine.

Las anulaciones I y C corrieron mientras se editaba
`check_prose_vocabulary.py` (sólo nombres de paquete, que ninguna prueba del
ciclo contiene); sus 47 aprobadas y la aserción caída no dependen de eso.
