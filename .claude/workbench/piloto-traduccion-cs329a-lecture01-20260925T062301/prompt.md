# Traducción de un fragmento de nota al español de México

Traduces un fragmento de una nota de curso escrita en LaTeX, del chino al
español de México. El `Item` al final es la ruta del fragmento en chino.

1. Lee el fragmento con `Read`.
2. Responde con el fragmento completo traducido entre una línea `<<<ES` y una
   línea `ES>>>`, sin nada más dentro. No escribas archivos: el ciclo escribe
   la traducción a partir de tu respuesta.

## Qué se traduce y qué no

- Se traduce toda la prosa en chino: párrafos, títulos de sección, títulos y
  texto de las cajas, pies de figura, notas al pie, celdas de tablas, etiquetas
  de TikZ y comentarios dentro de los listings.
- **No cambia** nada de la estructura: los comandos de LaTeX, `\label`,
  `\ref`, rutas de imágenes, URLs, fórmulas (salvo el texto chino dentro de
  `\text{}`), el código de los listings y el número de líneas de cada listing.
- No agregues ni quites contenido, ni resumas. Una traducción fiel, no una
  reescritura.

## Cómo se escribe

- Español de México profesional, sin coloquialismos ni clichés («la regla de
  oro», «a grandes rasgos», «chamba»).
- Sin spanglish: ni verbos hechos de una raíz inglesa (`testear`, `deployear`)
  ni calcos.
- **Significante contra significado:** traduce lo que el texto quiere decir, no
  la forma de las palabras. Un término técnico no se sustituye por una palabra
  española que se le parece y nombra otra cosa.
- Los términos técnicos se quedan en inglés, como ya están en la nota en chino.
- Nombres propios en chino: pinyin con el original entre paréntesis la primera
  vez que aparecen en el fragmento, por ejemplo `Yao Shunyu (姚顺雨)`.
- Cifras con punto decimal y coma de millares (`2,021`, `0.5`).
- Puntuación del español: `: ; , .` en lugar de `：；，。`.

## Glosario (obligatorio)

| Término | Decisión | Forma es-MX | Significado | Formas prohibidas |
|---|---|---|---|---|
| checkpoint | keep | — | estado guardado de los parámetros de un modelo durante o después del entrenamiento | puesto fronterizo|punto de comprobación |
| embedding | keep | — | representación vectorial densa de un token, una palabra u otro objeto | imbibición |
| fine-tuning | keep | — | ajuste de un modelo preentrenado con datos de una tarea específica | — |
| prompt | keep | — | texto de entrada con el que se le indica una tarea a un modelo de lenguaje | incitador |
| token | keep | — | unidad mínima en la que el tokenizer divide el texto | criptoficha |
| tokenization | translate | tokenización | división del texto en tokens, la operación que realiza el tokenizer | — |
| transformer | keep | — | arquitectura de red neuronal basada en atención (Vaswani et al., 2017) | transformador de potencia|transformador |

## Etiquetas de estructura (se traducen siempre así)

- `本章小结` → `Resumen de la sección`
- `总结与延伸` → `Síntesis y ampliación`
- `拓展阅读` → `Lecturas adicionales`
- `读图` → `Lectura de la figura`
- `背景概念` → `Concepto previo`
- `术语表` → `Glosario`
- `术语消化` → `Términos clave`
- `课堂提示` → `Nota de clase`
- `老师强调` → `el docente enfatiza`
- `来源` → `Fuente`
