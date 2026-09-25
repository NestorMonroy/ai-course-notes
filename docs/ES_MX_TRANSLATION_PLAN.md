# Plan de traducción es-MX: traductor + verificador + memoria con gates

Versión 1.0 — adapta a la traducción del corpus el plan de corrección
iterativa 2.2.0 (agente + verificador + memoria persistente). Su lección
central se conserva tal cual: **un paso que se puede saltar, eventualmente se
salta**. Por eso los pasos proactivos (escribir la memoria y barrer el corpus
con ella) no son parte de una secuencia que se recorre de buena fe: son gates
que detienen el ciclo con un error explícito, implementados como script, no
como prosa.

Este documento es un plan: nada de lo que describe como «nuevo» existe todavía.

## 1. Alcance, medido

| Magnitud | Valor | Cómo se midió |
|---|---|---|
| Notas a traducir | 370 `*-notes.tex` | `rglob('*-notes.tex')`, sin `.venv` ni plantillas |
| Texto chino | 2,306,404 caracteres Han, 13.2 MB | regex `[一-鿿]` sobre las 370 |
| Tamaño por nota | mediana 34,984 bytes; p90 60,237; máximo 95,677 (`cs25-v6/lecture01`) | `find -printf %s` |
| Invariantes | 9,059 cajas · 6,486 figuras · 931 fórmulas · 308 listings | regex sobre las 370 |
| Capítulos incluidos | 9 `lectureXX-chapter.tex` de `self-evolving-agents-2026`, 11,651 Han | `\input` de contenido |
| Preámbulos compartidos | `cs25-preamble` (50 notas), `cs153` (11), `cs336` (5), `notes-shared` (8); cargan `ctex` | `\input` de preámbulo |
| TikZ | 151 bloques, 93 con chino | regex sobre `tikzpicture` |
| Imágenes con texto chino incorporado | 338 PNG que dibuja `render_zhangxiaojun_concept_figures.py` (339 líneas con chino) | rutas en el script |

*Métrica:* conteo léxico sobre el código fuente. *Ciega a:* texto chino dentro
de imágenes que no genera ese script (capturas de pantalla, diapositivas); no
hay forma de verlo sin OCR y queda como riesgo (sección 10).

**La unidad de traducción** es la nota más sus capítulos. Los preámbulos
compartidos se traducen una vez por curso (su `.es-mx.tex`), antes que las
notas que los incluyen. Las 338 imágenes son una pista aparte: el script se
parametriza por idioma y regenera `*.es-mx.png`.

## 2. Lo que se automatiza antes de traducir

El traductor es la pieza cara y la única con juicio. Todo lo que es regla fija
se hace con script, antes o después de él, para que su trabajo sea solo la
prosa:

| Pieza | Qué hace | Base |
|---|---|---|
| `localize_preamble.py` (**nuevo**) | convierte al es-MX cualquier preámbulo: el de cada nota, los 4 compartidos (`cs25`, `cs153`, `cs336`, `notes-shared`) y las plantillas (`notes-template.tex`, `cs336-2026-notes-template.tex`). Cambia `ctex` por `fontspec` + `polyglossia` (variante mexicana), `extendedchars` y los nombres de `listings`, y traduce con una tabla fija las etiquetas que se repiten (`视频作者/频道`, `发布日期`, `视频时长`, `课程官网`, `视频链接`, `制作规范`, `课堂提示` de `\teachervoice`, `来源` de `\figsource`). El chino que no reconoce lo reporta, no lo adivina. | las etiquetas del perfil de `note_language.py` y los dos defectos que ya corrigió la plantilla es-MX (acentos en listings, «Listing») |
| Lematización (**existe desde `b9b4209`**) | el eje de spanglish de V4 consulta la tabla de lemas del español de spacy-lookups-data: una forma con lema es un verbo español (`horneado`, `formateado`), sin umbral ajustado a mano | `es_lemma_lookup`, 491,547 formas |
| Léxicos es/en (existen) | los ejes de palabra inventada, inglés sin glosario y spanglish de V4 | `es_lexeme_prob`, `en_lexeme_prob` |
| `suggest_term.py` (existe) | fila candidata del glosario desde IATE filtrado a informática y los léxicos | glosario |
| Figuras con texto (**existe desde `cc36a64`**) | `render_zhangxiaojun_concept_figures.py --lang es-mx` regenera las 338 imágenes como `*.es-mx.png` desde `tools/lang/es-mx/figure_text.tsv`; rehúsa (exit 3) si falta una cadena y `--extract` lista las que faltan: **2,531 cadenas, 56,747 caracteres**, medido | sus cadenas se traducen una vez, como un glosario |

Lo que no se automatiza es la prosa: la tabla de lemas y los léxicos dicen si
una palabra existe y de qué idioma es, no si la traducción dice lo mismo que el
original.

### 2.1 Memoria y anchura del pool: dos cotas distintas

**La memoria la hace cumplir GNU Parallel mientras el pool corre.**
`translate` pasa `--memfree 3G` a `headless-pool` (THYROX `bfb4eb15`), que tiene
dos efectos:

- **Admisión:** no se lanza un ítem si la memoria libre está por debajo de la cota.
- **Aplicación:** si la memoria baja de la mitad de la cota, se mata el trabajo
  más joven y se vuelve a encolar.

Los 3G dejan lugar a un `tsc` de 2 GB en paralelo. Una estimación estática al
lanzar no reacciona a lo que empiece después y duplica este mecanismo, así que
no se usa.

**La anchura (`--width`, 10 por defecto) solo acota la concurrencia contra la
API.** Sus límites de tasa (429) no se ven desde el contenedor, y 10 es lo que
el piloto corrió sin ningún 429. Si aparece uno, se baja con `--width` y se
registra en el banco.

La anchura **no** se deriva de la carga. Una primera versión lo hacía y tenía
tres defectos, que señaló el ejecutor:

1. **Contaba procesos, no ítems.** Usaba 116 MB, que es la cifra por proceso.
   Cada ítem son dos procesos: 232 MB por ítem, medido con 33 procesos y 17 ítems.
2. **La carga a un minuto mide a los otros procesos, no al pool.** Un `tsc` en
   paralelo la sube a 3.82 en 4 núcleos, y la fórmula daba anchura 1 durante toda
   la ejecución.
3. **Se decidía una sola vez, al lanzar.**

Si hace falta una anchura automática, se mide la memoria **por ítem** (la suma
del árbol de procesos) y los núcleos libres **al arrancar el pool**, nunca a
partir de la carga que producen otros.

## 3. Los tres papeles, adaptados

| Plan 2.2.0 | Aquí | Pieza |
|---|---|---|
| Agente | **Traductor**: una conversación `claude -p` por unidad, que lee la nota zh y escribe su `.es-mx.tex` | `headless-pool` de THYROX vía `tools/thyrox/run`, con `--tools Read,Write` (su default es solo `Read`) |
| Verificador | **Batería determinista** por unidad (sección 4) | scripts de `tools/scripts/` |
| Memoria | **Dos memorias persistentes**, versionadas | `tools/lang/es-mx/glossary.tsv` (decisiones por término, existe) y `tools/lang/es-mx/translation_memory.jsonl` (patrones, nuevo) |

La diferencia de fondo con la corrección: aquí la memoria **no solo sirve para
barrer lo ya hecho, también previene**. Cada `fix_generico` que sea una regla
de traducción entra a la plantilla del traductor del lote siguiente, así que el
mismo error no se vuelve a producir, además de corregirse donde ya se produjo.

## 4. El verificador

| # | Verificación | Estado | Qué detecta |
|---|---|---|---|
| V1 | **Paridad estructural zh ↔ es-MX** (`check_translation_parity.py`) | **nuevo** | mismas secciones, cajas por tipo, figuras con las mismas rutas de imagen, fórmulas, listings con código idéntico byte a byte, `\label`/`\ref`, URLs de `\href` y columnas de tablas. Traducir no puede perder ni inventar estructura. |
| V2 | **Chino residual** (dentro de V1) | **nuevo** | caracteres Han fuera de los originales entre paréntesis que la regla de nombres permite |
| V3 | **Términos que se quedan en inglés** (dentro de V1) | **nuevo** | un término del glosario `keep` presente en la nota zh que no aparece en la es-MX (la fuente ya los tiene en inglés) |
| V4 | `check_prose_vocabulary.py` | existe | palabra inventada, forma prohibida, spanglish, inglés sin glosario |
| V5 | `check_note_coverage.py` + `check_quality.sh` con perfil es-MX | existe | rasgos didácticos (lectura de figura, resúmenes, glosario, voz del docente) |
| V6 | Compilación doble con XeLaTeX | existe (guard `require_texlive` de THYROX) | LaTeX roto, TikZ roto, paquetes |
| V7 | QA visual del PDF (`render_pdf_qa.py` + hoja de contacto) | existe | maquetación; **por muestreo**, requiere mirar |

Todas las de V1–V6 dan una **señal** por hallazgo con forma estable
(`<verificación>:<clave>`, por ejemplo `parity:boxes`, `prose:english:weights`,
`compile:polyglossia.sty`). Esa señal es la que la memoria registra y la que el
barrido busca.

*Ciega a:* el significado. V1–V6 miden forma; una traducción fluida con otro
sentido pasa. Por eso V7 y la revisión por muestreo (sección 8) no son
opcionales.

## 5. La memoria de patrones

`tools/lang/es-mx/translation_memory.jsonl`, una entrada por línea, versionada
(no se borra al terminar un lote). Cuatro campos obligatorios, los del plan
2.2.0, más el tipo de arreglo:

```json
{"patron": "el traductor traduce 'checkpoint' como 'punto de control'",
 "senal_del_verificador": "parity:keep-term:checkpoint",
 "fix_generico": {"tipo": "prompt", "regla": "checkpoint se queda en inglés"},
 "archivos_donde_ya_se_aplico": ["cs329a/lecture01/lecture01-notes.es-mx.tex"]}
```

`fix_generico.tipo` decide cómo se aplica: `glossary` (fila nueva en el
glosario), `prohibited` (forma prohibida), `prompt` (regla en la plantilla del
traductor), `mechanical` (sustitución exacta aplicada por script) o `manual`
(requiere juicio; el barrido la marca y no la aplica sola).

## 6. El ciclo, con los gates integrados

```
MEMORIA = translation_memory.jsonl + glossary.tsv   (persisten entre lotes)

por cada lote (un curso):
    0. Construir la plantilla del traductor desde la MEMORIA
       (reglas `prompt` y el glosario completo)
    1. Traducir el lote (headless-pool, una unidad por item)
    mientras (señales > 0):
        2. Ejecutar el Verificador (V1–V6) sobre el lote
        3. Para cada grupo de señales que NO coincide con un patron de la MEMORIA:
            a. Corregir la causa raiz de ese grupo
            b. Escribir a la MEMORIA una entrada con los 4 campos

               *** GATE A (translation_gate.py memory): una entrada sin los
                   4 campos, o una señal nueva sin entrada, DETIENE el ciclo
                   con exit 2. No se continua al paso 4. ***

        4. Para cada patron de la MEMORIA:
            a. Buscar su señal en TODAS las notas es-MX ya traducidas,
               no solo en el lote
            b. Aplicar el fix_generico a cada instancia (o marcarla si es
               `manual`) y actualizar archivos_donde_ya_se_aplico
            c. Registrar el barrido: patron, notas revisadas, instancias

               *** GATE B (translation_gate.py sweep): si en esta iteracion
                   hay >= 1 patron en la MEMORIA y el registro de barrido no
                   cubre a todos, DETIENE el ciclo con exit 2 antes de volver
                   al paso 2. ***

        5. Volver al paso 2

    *** GATE C (translation_gate.py batch): el lote se cierra solo con
        0 señales de V1–V6 en todas sus unidades y la muestra de V7 revisada. ***
```

Los gates viven en un script con pruebas y control de anulación, no en este
documento. El registro de cada iteración (señales, entradas escritas,
barridos) va a un banco en `.claude/workbench/`, que se versiona.

## 7. Cómo verificar que los gates se respetaron

Antes de aceptar un lote, en su banco y no en el conteo de señales:

1. **¿Hay al menos una entrada de memoria con los 4 campos por cada grupo de
   señales nuevo?** Una bitácora de «nota X corregida, nota Y corregida» sin
   entradas estructuradas es la falla que el plan 2.2.0 observó.
2. **¿Algún barrido cubrió varias notas con un patrón ya guardado?** Si cada
   corrección del registro corresponde a una sola nota señalada en esa misma
   iteración, el paso 4 no se ejecutó.
3. **Iteraciones contra unidades.** Si el número de iteraciones de un lote se
   acerca al de unidades con señal, el ciclo corrió en modo reactivo. `translation_gate.py
   report` lo publica por lote.

## 8. Fases

| Fase | Qué | Criterio de salida |
|---|---|---|
| 0. Herramientas | con TDD y control de anulación: `localize_preamble.py` (y con él las plantillas es-MX que faltan, `cs336-2026-notes-template.es-mx.tex` entre ellas, y los 4 preámbulos compartidos), `check_translation_parity.py` (V1–V3), `translation_memory.jsonl` y `translation_gate.py` (gates A, B, C y `report`), la plantilla del traductor y el script de figuras parametrizado por idioma | pruebas en verde; cada gate rehúsa en su caso negativo |
| 1. Piloto de una nota | una nota corta y representativa, con figura, caja, fórmula y listing | V1–V6 en verde; **se miden** tokens de entrada y salida, tiempo y dinero por unidad (la salida JSON de `claude -p` trae el uso); se recalibra el factor 4.38 letras/Han del perfil con prosa real |
| 2. Piloto de curso | `cs329a` (9 notas, 34,785 Han): el lote más pequeño con estructura de curso completa | gates A y B ejercidos al menos una vez; reporte de iteraciones contra unidades |
| 3. Escalado | un curso por lote, en el orden que se decida; la anchura del pool derivada de los recursos (sección 2.1), con el factor por núcleo corregido en la fase 1 | gate C por lote |
| 4. Cierre | sitio es-MX (`generate_site.py --lang es-mx`), conteos del README, `TRACKING.md` | sitio compila en `--strict` |

## 9. Costo: se mide en tokens, no se estima

El costo se mide en tokens, por separado en los cuatro componentes que THYROX
ya distingue (`src/transcript/usage.py`): `input`, `cache_creation`,
`cache_read` y `output`. No se reporta en dinero: el peso de cada componente es
del contrato de precio del modelo, no del ciclo. `translation_loop.py usage
--bench B` suma los componentes de cada item, escribe `usage.tsv` por
fragmento y mide las letras del es-MX por carácter Han del original, que es el
dato con el que se recalibra el factor 4.38 del perfil.

El corpus pide del orden de 2.3 millones de caracteres Han de entrada más el
LaTeX que los rodea (13.2 MB), y una salida mayor, porque el español ocupa más
caracteres por idea. La extrapolación sale de la fase 1, con la distribución de
tamaños de la sección 1, no con un promedio supuesto.

**Primera medición: el intento fallido del piloto** (10 fragmentos de
`cs329a/lecture01`). Cada ítem pagó un piso de **~24,000 `cache_read` y ~6,000
`cache_creation`**, que son el prompt de sistema y la plantilla, antes de
traducir nada. En los fragmentos de 3.4 a 5.3 KB, la traducción que el modelo
devolvió en su respuesta midió **~7,000 `output`**. Totales: 80 `input`, 90,414
`cache_creation`, 375,637 `cache_read` y 37,784 `output`.

Ese intento destapó dos defectos del contrato y se corrigieron:

1. `claude -p` bloquea `Write` bajo `.claude/`. Por eso ahora el modelo solo lee
   y devuelve la traducción entre `<<<ES` y `ES>>>`, y el ciclo la escribe.
2. El ítem llevaba dos rutas separadas por un tabulador, y `headless-pool` parte
   el índice con `--colsep '\t'`, así que la segunda ruta se perdía.

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| El verificador no ve el significado | V7 por muestreo y revisión humana de una fracción por lote |
| Texto chino incorporado en imágenes que no genera el script (capturas) | inventario por muestreo en la fase 1; sin OCR no hay medición completa |
| Una nota grande excede lo que una conversación produce de una vez (la mayor tiene 95,677 bytes) | la fase 1 mide el límite; si hace falta, la unidad pasa a ser la sección |
| TikZ roto al traducir etiquetas (93 bloques) | V6 lo detecta; patrón `mechanical` si se repite |
| La memoria crece con reglas contradictorias | GATE A rechaza una señal que ya tiene patrón; una contradicción se resuelve editando la entrada, no agregando otra |

## 11. Decisiones pendientes

1. **Modelo** del traductor: `claude-sonnet-5`, sostenido por los pilotos.
   - El fallo del primer intento fue del contrato, no del modelo.
   - Fase 2: los defectos reales del traductor fueron unas 15 palabras en
     inglés introducidas, un `\enquote` y un cliché, sobre 75 fragmentos.

   **Se reabre** si, tras las reglas nuevas de la plantilla, la retraducción de
   la fase 2 sigue introduciendo inglés donde el original escribe chino. En ese
   caso se hace una prueba A/B con otro modelo sobre los mismos fragmentos,
   comparando señales y tokens, antes de cambiar.
2. **Techo de costo**, después de la fase 1. La anchura ya no es una decisión: se deriva (sección 2.1).
3. **Orden de los cursos** en la fase 3.
4. **Fracción de revisión humana** por lote.
5. **Publicar** el sitio es-MX en GitHub Pages o solo construirlo.
