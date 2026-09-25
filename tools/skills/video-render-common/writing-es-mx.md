# Notas en español de México (es-MX): complemento de `writing-and-figures.md`

Este archivo **no sustituye** a `writing-and-figures.md`: todas sus reglas
(subtítulos, transcripción, figuras, QA visual del PDF) aplican igual. Aquí solo
se reemplaza lo que depende del idioma. Si una regla de aquí contradice a la
base, gobierna esta para las notas es-MX.

## Archivo y plantilla

- La nota se llama `<lecture>-notes.es-mx.tex` y vive junto a la nota en chino
  (`<lecture>-notes.tex`), en el mismo directorio y con las mismas imágenes.
- Se parte de `tools/templates/notes-template.es-mx.tex` (XeLaTeX con
  `polyglossia`, variante mexicana), no de `notes-template.tex`.
- Los scripts de QA reconocen el idioma por ese nombre; el perfil de etiquetas
  vive en `tools/scripts/note_language.py`.

## Etiquetas que marcan cada rasgo didáctico

Los scripts de QA cuentan estas etiquetas. Se eligieron por la función que
cumplen en la nota, no por la palabra: `本章小结` dice «resumen de este
capítulo», pero cierra cada `\section`, por eso es «Resumen de la sección».

| zh | es-MX | Dónde va |
|---|---|---|
| `本章小结` | `Resumen de la sección` | `\subsection{...}` al cerrar cada sección |
| `拓展阅读` | `Lecturas adicionales` | `\subsection{...}` opcional con enlaces externos |
| `总结与延伸` | `Síntesis y ampliación` | `\section{...}` final del documento |
| `读图` | `Lectura de la figura` | título de la caja que explica una figura |
| `背景概念` | `Concepto previo` | título de la caja de un concepto de base |
| `术语表` / `术语消化` | `Glosario` / `Términos clave` | tabla o caja de terminología |
| `课堂提示` | `Nota de clase` | título de la caja con la voz del docente |
| `老师强调` | `el docente enfatiza` | en la prosa, al atribuir un énfasis del curso |

Metadatos: `\noteauthors{Elaboradas a partir de materiales públicos del curso}`
o `Elaboradas a partir de la clase de [Nombre]`; `\notedate{}` con la fecha de
publicación o el periodo del curso (`Primavera de 2025` o `2025-03-15`), nunca
`\today`.

## Redacción

- **Español de México, profesional y sin coloquialismos.** Nada de «chamba»,
  «padrísimo», «a grandes rasgos», «la regla de oro».
- **Sin spanglish.** Ni verbos hechos de una raíz inglesa (`testear`,
  `deployear`, `commitear`) ni sustantivos calcados (`deployeo`).
- **Los términos técnicos se quedan en inglés** (`embedding`, `checkpoint`,
  `fine-tuning`, `token`, `prompt`, `Transformer`) y se explican en su primer
  uso. Un término técnico se traduce solo si el glosario del repositorio lo
  indica.
- **Significante contra significado.** Se traduce lo que el texto quiere decir,
  no la forma de la palabra. Un término técnico no se sustituye por una palabra
  española que se le parece pero nombra otra cosa: `embedding` no es
  «imbibición» (química), `transformer` no es «transformador» (electricidad),
  `library` no es «librería».
- **Falsos amigos frecuentes:** `eventually` es «con el tiempo», no
  «eventualmente»; `actually` es «en realidad», no «actualmente»; `remove` es
  «retirar» o «eliminar», no «remover».
- **Nombres propios en chino:** pinyin con el original entre paréntesis en su
  primera aparición, por ejemplo `Yao Shunyu (姚顺雨)`.
- **Cifras:** punto decimal y coma de millares, como en México (`2,021`, `0.5`).

## Cuando la fuente es la nota en chino

La nota es-MX traduce el contenido de la nota zh; no la resume ni le agrega
material. Se conservan todas las figuras, cajas, fórmulas, tablas y listings, y
se traducen títulos, pies de figura, notas al pie y texto de las cajas. El
código no se traduce; sus comentarios sí.

## QA

Además del QA de la base (`check_quality.sh`, `check_note_coverage.py`,
compilación doble con XeLaTeX y QA visual del PDF), que ya reconocen las notas
es-MX por su nombre.
