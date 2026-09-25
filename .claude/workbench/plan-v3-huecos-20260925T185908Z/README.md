# Plan v3 contra el código: tres huecos cerrados

Pregunta del ejecutor (2026-09-25): ¿el plan de corrección iterativa 3.0.0
está en el PLAN, y se actualizó con él? Cotejo punto por punto de la sección 6
de `docs/ES_MX_TRANSLATION_PLAN.md` y de `translation_loop.py`:

1. **Efecto neto sin script.** El plan decía «midiendo su efecto neto» y el
   código tenía 0 apariciones de neto/`net_effect`/«introduc». Ahora:
   `translation_loop.py measure --decision D`, `decisions.tsv` de solo
   agregar, `measures/NNN-<ISO>.jsonl`, salida 4 con neto negativo.
2. **Agrupar por nombre junta causas distintas.** Censo de señales de todas
   las iteraciones: `compile:error`, `compile:missing-glyph` y `coverage:*`
   son genéricas; `compile:missing-glyph` juntaba «（» (U+FF08) y «张» (Han).
   Ahora `cause_key`: por carácter (todos los Han, una causa) y por mensaje
   más comando de `l.NN`.
3. **Límites no declarados.** Solape de rutas (gana la primera), un punto de
   datos, causa compartida que puede no serlo, `measure` ciego al significado:
   declarados en la sección 6.

Métrica del censo: nombres de señal de `iterations/*/signals.jsonl` de todos
los lotes. Ciega a: las señales `parity:*`, que no aparecieron en esos datos.

## TDD

- `red.txt`: `KeyError: 'compile:missing-glyph:han'` y `invalid choice:
  'measure'`.
- `derived.txt`: el comando que deriva el subconjunto y su resultado.
- `annul-summary.txt`: A (sin `cause_key`) y B (sin normalizar Han) hacen
  caer sólo la prueba de agrupación. **C no discriminó**: la segunda mitad de
  la prueba de `measure` corregía «pools», y contra la iteración también daba
  1 resuelta y 0 introducidas. Se reescribió con una medición sin cambios
  (0/0/0 contra la anterior; 1/1 contra la iteración).
- `annul-2-summary.txt`: C y D (sin la salida 4) hacen caer sólo la prueba de
  `measure`; 46 pasan y la xfail de capítulos sigue igual en las cuatro.
