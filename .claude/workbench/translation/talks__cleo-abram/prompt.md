# Traducción de un fragmento de nota al español de México

Traduces un fragmento de una nota de curso escrita en LaTeX, del chino al
español de México. El `Item` al final es la ruta del fragmento en chino.

1. Lee el fragmento con `Read`.
2. Responde con el fragmento completo traducido entre una línea `<<<ES` y una
   línea `ES>>>`, sin nada más dentro. No escribas archivos: el ciclo escribe
   la traducción a partir de tu respuesta.

## La fuente original en inglés

La nota en chino traduce una clase dada en inglés. Si junto al fragmento existe
`source.srt` (el mismo directorio), es la transcripción original de la clase.
Cuando dudes de qué significa un término que el original escribe en chino,
búscalo ahí con `Grep` (por ejemplo, el nombre inglés que sospechas) para ver
cómo lo dijo quien dio la clase. No leas la transcripción completa y no la
traduzcas: sirve solo para elegir el significado correcto.

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
- Los términos técnicos se quedan en inglés **solo si la nota en chino ya los
  escribe en inglés** o si el glosario dice `keep`. Si el original escribe el
  término en chino (机器学习, 数据集), se traduce al español (aprendizaje
  automático, conjunto de datos); no se sustituye por su nombre en inglés.
- Nombres propios en chino: pinyin con el original entre paréntesis la primera
  vez que aparecen en el fragmento, por ejemplo `Yao Shunyu (姚顺雨)`.
- Cifras con punto decimal y coma de millares (`2,021`, `0.5`).
- Puntuación del español: `: ; , .` en lugar de `：；，。`. Las comillas del
  original (`“ ”`, `「 」`) se escriben «así».
- No uses comandos de paquetes que la nota no carga (`\enquote`, `\textquote`);
  si el original no usa un comando, la traducción tampoco.
- Escribe con todas las tildes y la eñe: `traducción`, `señal`, `también`.

## Glosario (obligatorio)

| Término | Decisión | Forma es-MX | Significado | Formas prohibidas |
|---|---|---|---|---|
| batch | translate | lote | grupo de ejemplos que se procesa junto en un paso de entrenamiento o inferencia | — |
| checkpoint | keep | — | estado guardado de los parámetros de un modelo durante o después del entrenamiento | `puesto fronterizo`, `punto de comprobación` |
| embedding | keep | — | representación vectorial densa de un token, una palabra u otro objeto | `imbibición` |
| factual | translate | factual | relativo a los hechos; «exactitud factual» | — |
| fine-tuning | keep | — | ajuste de un modelo preentrenado con datos de una tarea específica | — |
| interpretability | translate | interpretabilidad | grado en que una persona puede entender por qué un modelo produce una salida | — |
| iterable | translate | iterable | que puede repetirse por iteraciones; adjetivo regular de «iterar» | — |
| observability | translate | observabilidad | capacidad de inferir el estado interno de un sistema a partir de sus salidas | — |
| pool | translate | conjunto | conjunto de modelos o recursos disponibles para elegir (模型池) | — |
| pre-training | translate | preentrenamiento | entrenamiento inicial de un modelo sobre un corpus general, antes de ajustarlo a una tarea | — |
| prompt | keep | — | texto de entrada con el que se le indica una tarea a un modelo de lenguaje | `incitador` |
| prompting | keep | — | técnica de formular el prompt para obtener una conducta del modelo | `incitar` |
| scalability | translate | escalabilidad | capacidad de un sistema de crecer en carga sin rediseñarse | — |
| token | keep | — | unidad mínima en la que el tokenizer divide el texto | `criptoficha` |
| tokenization | translate | tokenización | división del texto en tokens, la operación que realiza el tokenizer | — |
| tokenize | translate | tokenizar tokenizado tokenizada tokenizados tokenizadas tokeniza tokenizan | dividir un texto en tokens; verbo de «tokenización» | — |
| transformer | keep | — | arquitectura de red neuronal basada en atención (Vaswani et al., 2017) | `transformador de potencia`, `transformador` |
| render | translate | renderizar renderizado renderizada renderizados renderizadas | generar una imagen a partir de un modelo de escena | — |
| productization | translate | conversión en producto | convertir una capacidad técnica en un producto utilizable | `productización` |

## Frases fijas (se traducen siempre así, en todas las notas)

- `自我改进 AI Agent` → `Agentes de IA que se automejoran`

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

## Formas prohibidas (no aparecen en la traducción)

`regla de oro`, `la clave esta en`, `la clave está en`, `a ojo`, `frases hechas`, `piedra angular`, `a grandes rasgos`, `al final del dia`, `al final del día`, `en pocas palabras`, `por si las dudas`, `chamba`, `chambear`, `padrisimo`, `padrísimo`, `me fui de boca`, `darle vuelta al asunto`, `sin mas ni mas`, `sin más ni más`, `a la mala`, `de un jalon`, `de un jalón`, `corrida`, `corridas`, `tanda`, `tandas`, `agarrar`, `agarra el`, `meterle`, `sacarle`, `correr el`, `correr la`, `correr los`, `correr las`, `a correr`, `monorepo`, `librería` → biblioteca, `libreria` → biblioteca, `librerías` → bibliotecas, `librerias` → bibliotecas, `remover` → retirar, `removerse` → retirarse, `removerlo` → retirarlo, `removido` → retirado, `removidos` → retirados, `removida` → retirada, `removidas` → retiradas, `removió` → retiró, `removio` → retiró, `removieron` → retiraron, `removiendo` → retirando, `mergear`, `mergeado`, `debuguear`, `debugueo`, `loguear`, `logueo`, `chequear`, `chequeo`, `deployar`, `deployado`

## Reglas aprendidas en lotes anteriores (obligatorias)

- Un término que el original escribe en chino se traduce al español; se queda en inglés solo si el original lo escribe en inglés o el glosario dice keep.
- La plantilla cita la lista entera de prohibited_forms.txt; ninguna aparece en la traducción.
- Sin comandos de paquetes que la nota no carga; los entornos del original se conservan (translate rechaza el fragmento que los cambia).
