# Fase 2: cs329a, lecciones 02 a 09

`translation_loop.py translate` sobre 8 notas: 83 fragmentos (75 al modelo y 8
cabeceras copiadas por no tener chino), anchura 10, `--memfree 3G`. **123 s de
pared, 75 de 75 con marcadores.**

## Tokens por componente (`usage.tsv`)

| | input | cache_creation | cache_read | output |
|---|---:|---:|---:|---:|
| 75 ítems | 300 | 341,960 | 1,100,100 | 102,675 |

Letras del es-MX por carácter Han sobre los fragmentos: 5.95.

## Primera verificación (`signals-1.jsonl`): 36 señales

| Clase | Cuántas | Lectura |
|---|---:|---|
| `prose:english` | 22 | 3 son español (`compare`, `complete`, `explore`: subjuntivos); el resto es inglés que el traductor introdujo donde el original escribe chino (`throughput`, `backbone`, `machine learning`) |
| `prose:invented` | 7 | derivaciones con prefijo culto sobre palabras atestiguadas (`autoverificación`, `posentrenamiento`) e `interpretabilidad` |
| `parity:keep-term:token` | 3 | falso positivo: el chino no flexiona; el original dice «token» y la traducción, bien, «tokens» |
| `prose:spanglish` | 1 | `externalizar` es español |
| `prose:forbidden` | 1 | «la clave está en», un cliché |
| `coverage` | 1 | lecture02: el original pasa `readfig` por una coincidencia (图景…说明), no por explicar sus figuras |
| `compile` | 1 | lecture02: `\enquote`, un comando que la nota no carga |

Estado: **borrador**. Las correcciones del verificador (diccionario es_MX,
prefijos, formas verbales) y las reglas nuevas del traductor ya están; faltan
la retraducción de los fragmentos con inglés introducido, la regla de
inflexión de `keep-term`, la de `readfig` estricto y el gate B.
