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
