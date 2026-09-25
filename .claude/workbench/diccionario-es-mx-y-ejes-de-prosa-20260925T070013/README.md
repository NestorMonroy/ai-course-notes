# Diccionario es_MX y ejes de prosa

Los ejes de prosa del verificador leían forma y no pertenencia. La fase 2 lo
destapó: `compare` (subjuntivo de *comparar*) salía como inglés,
`externalizar` como spanglish, y el español sin tildes (`traduccion`) no salía.

## Qué se cambió

| Pieza | Antes | Ahora |
|---|---|---|
| diccionario | frecuencia y lema de spaCy | hunspell es_MX construido desde RLA-ES (`fb279606`, 59,411 entradas) |
| eje `english` | inglés si es más frecuente en inglés | además, que el diccionario es_MX no la acepte |
| eje `spanglish` | raíz inglesa + terminación española | además, que el diccionario no la acepte |
| eje `invented` | sin atestiguar en el léxico | además, que no sea prefijo culto + palabra atestiguada (`autoverificación`) ni la acepte el diccionario |
| eje `unaccented` (nuevo) | — | forma rechazada cuya versión con tildes o eñe el diccionario acepta |
| `keep-term` de paridad | el término literal | el término o su plural inglés |
| herencia en el ciclo | inglés del original | inglés del original, también para `unaccented` (`precision`) |

## Controles de anulación (`annul.sh`, `annul.log`)

Cada guarda se retiró y cayó exactamente su prueba: el eje de tildes, el
diccionario en spanglish, el diccionario en inglés y el filtro de basura del
léxico (`reading→`). Los de `keep-term` plural, del gate de comentarios y de la
herencia se corrieron en línea y cayó la suya en cada caso. Uno no discriminaba
al principio: el de las comillas de shell. La línea de prueba no tenía `#`
entre comillas; ahora lo tiene y cae.

`suite-completa.log`: 145 pruebas en verde al cerrar el bloque.

## thyrox (`fd5610608`)

`thyrox_toolchain_require_hunspell` con los ejes de GNU parallel. Las pruebas
derivadas son 17: 14 en verde, y 3 que fallan igual en `HEAD` sin el cambio
(`thyrox-derivadas.txt`, `thyrox-run/`).

## Barrido de comentarios: tildes, eñe y formas prohibidas

Detonante: el ejecutor encontró «primera corrida» en un banco. `corrida`
está en `prohibited_forms.txt`, y la misma línea 54 de ese archivo documenta
el mismo episodio. Pasó porque ningún gate miraba los comentarios ni los
bancos: el de prosa solo revisa las notas `.tex`.

| Paso | Resultado |
|---|---|
| `check_comment_spelling.py` también reporta formas prohibidas | 12 usos reales de `corrida`, reescritos por su sentido (ejecución, iteración) |
| una forma entre `…` o «…» es cita, no uso | la plantilla y el glosario citan las formas prohibidas para prohibirlas |
| el idioma se decide por tramo y por documento | `AGENTS.md` (145 tramos en inglés contra 1) y `check_note_coverage.py` quedan fuera; antes el gate les proponía `names → ñames` |
| nombre propio: mayúscula que no abre oración | `Debian`, `LaTeX` |
| `--fix` sobre 57 archivos de la rama | 441 hallazgos → 0; las copias textuales de evidencia (`annul/orig/`, `zh-equiv/`) y los `prompt.md` enviados al modelo no se tocan |

Una heurística se descartó por la medición: tomar por inglesa una palabra que
el léxico inglés prefiere, en un tramo sin palabras funcionales. `fusion` tiene
frecuencia parecida en los dos léxicos, así que no discrimina. El comentario
inglés que la motivaba se tradujo, porque la convención del repositorio es
comentar en español.

**Pendiente en THYROX:** la convención ASCII sin tildes es del proveedor. Hay
`*Metrica:*` en 73 archivos, y `src/session/job_runs.py:221` lo escribe en los
registros de trabajos de cada consumer. Corregirla es un cambio de convención
del proveedor y queda a decisión del ejecutor.
