# Plan de traducción es-MX: traductor + verificador + memoria con gates

Versión 2.1. Adapta a la traducción del corpus el plan de corrección iterativa
en dos pasos:

- **de la 2.2.0** toma el agente, el verificador y la memoria persistente;
- **de la 3.0.0** toma las tres rutas según dónde vive la causa (sección 6).

La lección central se conserva: **un paso que se puede saltar, eventualmente
se salta**. Por eso los pasos proactivos (escribir la memoria, barrer el corpus
con ella, clasificar antes de retraducir) no forman una secuencia que se
recorre de buena fe: son gates y subcomandos que detienen el ciclo con un error
explícito, implementados como script, con pruebas y control de anulación.

**Estado:** las piezas de este plan existen en `tools/scripts/translation_loop.py`
y `translation_gate.py`. Las fases 0, 1 y 2 (cs329a) están cerradas; de la 3,
la ola 1 (filas 2 a 9 del plan) cerró en 0 señales. Lo medido en cada una está
en su banco, bajo `.claude/workbench/`.

**Cambios de la 2.1**, tras cotejar la sección 6 con la 3.0.0 punto por punto:
la 2.0 decía «midiendo su efecto neto» y el código no lo medía (0 apariciones);
agrupaba por nombre de señal, que junta causas distintas; y no declaraba los
límites de sus propias cifras. Los tres quedan cerrados en la sección 6.

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

`prepare` sigue los `\input`/`\include` de cada nota, también los anidados y
resueltos desde el directorio de la nota, que es desde donde XeLaTeX los
resuelve. Cada archivo incluido es una unidad con su propio `.es-mx.tex`, y la
nota apunta a él, también dentro de `\IfFileExists`. Un capítulo no pasa por
`localize` (sus reglas de metadatos caían sobre la prosa) y no se compila solo:
lo compila la nota que lo incluye.

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
| Agente | **Traductor**: una conversación `claude -p` por fragmento, con `--tools Read,Grep`. Lee el fragmento zh y **devuelve** la traducción entre `<<<ES` y `ES>>>`; el ciclo la escribe | `headless-pool` de THYROX vía `tools/thyrox/run`. `Write` quedó fuera porque `claude -p` lo bloquea bajo `.claude/` (primer intento del piloto) |
| Fuente original | la **transcripción en inglés** de la clase (`source.srt`, enlazada junto al fragmento): el traductor la consulta con `Grep` cuando duda de qué significa un término que el original escribe en chino | `english_source()` en `prepare`; 320 de las 370 notas tienen una |
| Verificador | **Batería determinista** por nota (sección 4) | `tools/scripts/` |
| Memoria | **Dos memorias persistentes**, versionadas | `tools/lang/es-mx/glossary.tsv` (decisiones por término, con fuente) y `tools/lang/es-mx/translation_memory.jsonl` (patrones) |

La memoria **no solo barre lo ya hecho, también previene**: la plantilla del
traductor se construye en cada iteración desde el glosario, la lista entera de
formas prohibidas y las reglas `prompt` de la memoria.

## 4. El verificador

| # | Verificación | Qué detecta |
|---|---|---|
| V0 | **Al recibir el fragmento** (`translate`) | sin marcadores `<<<ES`/`ES>>>`, o con otro multiconjunto de `\begin`/`\end` que el original: se rechaza y queda pendiente, antes de escribirse |
| V1 | Paridad estructural zh ↔ es-MX (`check_translation_parity.py`) | secciones, cajas por tipo, figuras e imágenes (`x.es-mx.png` cuenta como `x.png`), fórmulas, listings, `\label`/`\ref`, URLs, `\input` |
| V2 | Chino residual, en todo el documento (preámbulo incluido) | caracteres Han fuera de los originales entre paréntesis |
| V3 | Términos `keep` del glosario presentes en zh y ausentes en es-MX (el plural inglés cuenta) | un término técnico traducido fuera |
| V4 | `check_prose_vocabulary.py` con hunspell es_MX (RLA-ES) | palabra inventada (con prefijos cultos), forma prohibida, spanglish, inglés, español sin tildes ni eñe |
| V5 | `check_note_coverage.py` con perfil es-MX | rasgos didácticos |
| V6 | Compilación doble con XeLaTeX | el error del log con su línea `l.NN` (que nombra el comando), y los glifos que la fuente no tiene |
| V7 | QA visual del PDF, por muestreo | maquetación; requiere mirar |

**Herencia:** lo que el original ya trae no es defecto de la traducción. Cuenta
el inglés que la nota zh escribe (y su plural), y un error de cobertura que el
original también tiene. En el caso de `readfig` se mide con el marcador
estricto 读图, porque los patrones laxos del perfil zh casan por coincidencia.

**Veredicto completo o nada:** cada nota pedida tiene que reportarse. Una que
no se reporta (un proceso que murió) es `verify:incomplete` y la verificación
sale con 2. En cs329a, iteración 02, un proceso muerto se leyó como «sin
señales».

Todas dan una señal con forma estable (`<verificación>:<clave>`), que es la que
la memoria registra y la que `triage` clasifica. *Ciega a:* el significado. Por
eso V7 y la revisión humana por muestreo no son opcionales.

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

## 6. El ciclo: clasificar antes de asignar (tres rutas, plan 3.0.0)

La 2.2.0 suponía que todo error se resuelve donde el verificador lo señala. En
esta traducción no es así, y está medido: de las 36 señales de la primera
pasada de cs329a, **13 (36%) se resolvieron cambiando el verificador una
vez**, con 0 tokens. En el piloto, corregir `title=#1` en `localize_preamble`
evitó romper **838 definiciones en 275 archivos**. Por eso cada señal se
clasifica según dónde vive su causa antes de retraducir nada:

| Ruta | Cuándo | Cómo se resuelve | Juicio |
|---|---|---|---|
| **1. Determinista** | un arreglo `mechanical` de la memoria cubre la señal y su texto está en la nota | `sweep`: sustitución exacta en **los fragmentos** (la fuente de verdad) y en las notas, de todos los lotes | no |
| **2. Causa compartida** | la misma **causa** en dos notas o más, de cualquier lote; o una causa en el verificador, el glosario, la plantilla o un preámbulo compartido | una decisión por causa, en orden de frecuencia (`triage.tsv`), con `measure --decision` después de cada una y antes de la siguiente | sí, una vez por causa |
| **3. Local** | el resto | `retranslate` devuelve a pendientes solo los fragmentos que llevan la señal; la siguiente iteración los retraduce | sí, por fragmento |

```
MEMORIA = translation_memory.jsonl + glossary.tsv   (persisten entre lotes)
PLAN    = translation_loop.py plan  → translation/plan.tsv (un lote por curso, de menor a mayor)

por cada lote del PLAN:
    cycle --batch L --compile       # prepare → translate → assemble → verify, en iterations/NN/
    mientras (señales > 0):
        triage                      # rutas 1, 2 y 3, con la cola de la ruta 2 por frecuencia
        1. sweep                    # ruta 1, en fragmentos y notas de todos los lotes
                *** GATE B: el registro del barrido cubre todos los patrones ***
        2. una decisión por causa compartida (glosario con fuente, regla de la
           plantilla o del verificador con prueba y control de anulación) y su
           entrada de memoria; después, antes de la siguiente decisión:
           measure --decision "<causa → arreglo>"   # neto = resueltas - introducidas
                *** GATE A: toda señal tiene un patrón con los 4 campos ***
        3. retranslate --batch L    # ruta 3: solo fragmentos locales
        cycle --batch L --compile   # siguiente iteración
    *** GATE C: 0 señales en la última iteración y la muestra de V7 revisada ***
```

**La causa, no el nombre.** Una señal de prosa ya lleva su texto
(`prose:english:pools`) y ése es su agrupador. Las genéricas no:
`compile:missing-glyph` con «（» en una nota y «张» en otra son dos causas (el
paréntesis de ancho completo, que arregla la memoria mecánica, y la falta de
fuente CJK, que arregla xeCJK), y agrupadas por nombre contaban como una causa
compartida falsa. `cause_key` agrupa `compile:missing-glyph` por carácter, con
todos los Han como una sola causa (ninguno tiene glifo), y `compile:error` por
mensaje más el comando que nombra su línea `l.NN`. Es lo que la 3.0.0 pide
confirmar «tipo por tipo antes de unificar»: aquí la confirmación la hace la
clave, no quien lee la cola.

**El efecto neto de cada decisión se mide, no se supone.** `translation_loop.py
measure --decision D` verifica **todo** el corpus traducido (una fila del
glosario puede introducir señales en notas que estaban limpias) y compara, por
(nota, causa), con la medición anterior, que tiene el mismo alcance. Agrega
una fila a `translation/decisions.tsv` (solo se agrega: decisión, antes,
después, resueltas, introducidas, neto) y guarda la medición en
`translation/measures/NNN-<ISO>.jsonl`. Con neto negativo sale con 4: la
decisión se revierte antes de tomar la siguiente.

**La primera medición es la línea base y no lleva neto**, así que se toma
**antes** de la primera decisión: `measure --decision "línea base"`. La 2.1
comparaba, si no había medición anterior, contra la última iteración de cada
lote, y eso mezcla alcances. En su primer uso (`self-evolving-agents-2026`,
«internalize → interiorizar») dio **−6** a una decisión que resolvió su señal.
La iteración 06 había quedado sin ensamblar, con 0 señales, y los 5 preámbulos
compartidos no están en ninguna iteración, así que sus `variant` contaron como
introducidos. Esa fila de `decisions.tsv` se conserva tal cual (es de solo
agregar); la corrección está en el banco `linea-base-de-measure-*`.

**Límites de estas cifras, declarados.**

- **Las rutas se solapan y gana la primera.** Una causa con arreglo mecánico en
  la memoria es determinista aunque aparezca en varias notas; la precedencia
  es determinista, luego compartida, luego local, y `triage.tsv` muestra sólo
  la ruta ganadora.
- **Un punto de datos no es una tendencia.** Las cifras de esta sección
  (13 de 36 señales por el verificador en cs329a; 838 definiciones en el
  piloto) son de un lote y un momento cada una; `decisions.tsv` es el lugar
  donde se acumula la medición repetida.
- **Una causa compartida puede no serlo.** `cause_key` separa lo que su
  detalle distingue; dos errores con el mismo mensaje y el mismo comando pero
  causas distintas siguen juntos. Por eso la decisión se mide con `measure`, y
  un neto menor que el número de notas de la causa es la señal de que no era
  una sola.
- **`measure` ve lo que el verificador ve.** Un arreglo que empeora el
  significado sin tocar una señal da neto 0 (riesgo de la sección 10, V7).

**Fase 3, por olas con GNU Parallel.** Los lotes son independientes, así que
`translate_wave.sh --from N --to M --jobs J` lanza un
`translation_loop.py advance --no-sweep` por lote con `parallel -j J`:

- la anchura contra la API se reparte entre los trabajos (`10 // J`);
- el `--joblog` de Parallel es el registro de la ola;
- el barrido (ruta 1) y el triage (ruta 2) corren **una sola vez** al final de
  la ola, porque el barrido reescribe la memoria y dos en paralelo perderían
  entradas.

`advance` itera las rutas 1 y 3 por sí solo y sale con 3 cuando hace falta
juicio: una causa compartida, señales sin fragmento que retraducir, **una
señal que sobrevive a la retraducción de su fragmento** o el tope de
iteraciones. La tercera viene de `self-evolving-agents-2026`: «resolubilidad»
e «internalizar» volvieron iguales en tres retraducciones y sólo cedieron a
una fila del glosario; ahora el lote se detiene tras la primera retraducción
que las repite y las nombra. Sale con 5 si la cuenta llegó a su límite de
sesión (sección 9.1). Lo que pide juicio se decide entre olas.

**El registro de cada lote** vive en un banco estable,
`.claude/workbench/translation/<lote>/`, versionado:

- `iterations/NN/` guarda las señales, el uso de tokens y la lista de
  retraducción de cada ejecución, sin sobrescribir las anteriores;
- `translation/batches.tsv` recibe una fila por iteración (solo se agrega);
- `.claude/workbench/.last-bank` apunta al lote en curso.

## 7. Cómo verificar que los gates se respetaron

Antes de aceptar un lote, en su banco y no en el conteo de señales:

1. **¿Cada grupo de señales nuevo tiene una entrada de memoria con los 4
   campos?** `translation_gate.py memory` sobre cada `iterations/NN/signals.jsonl`.
2. **¿Las rutas 1 y 2 se agotaron antes de retraducir?** Un
   `retranslate.tsv` con señales `shared` o `deterministic` marcadas como
   `retranslate` indica que se saltó la clasificación.
3. **Iteraciones contra unidades.** `batches.tsv` da, por iteración, cuántos
   fragmentos se tradujeron y cuántas señales quedaron. Si las iteraciones se
   acercan al número de fragmentos con señal, el ciclo corrió en modo reactivo
   (`translation_gate.py report`).

## 8. Fases

| Fase | Qué | Estado |
|---|---|---|
| 0. Herramientas | `localize_preamble.py`, paridad, gates A/B/C, plantilla, figuras por idioma, ciclo | **cerrada**; cada pieza con prueba y control de anulación |
| 1. Piloto de una nota | `cs329a/lecture01` | **cerrada**: 0 señales, 22 páginas, QA visual; el primer intento falló por el contrato (banco `piloto-…-061536`) |
| 2. Piloto de curso | `cs329a`, lecciones 02 a 09, en `translation/cs329a/` | **en curso**: 36 → 23 → 8 → 6 → 3 señales en cinco iteraciones |
| 3. Escalado | un lote por curso según `translation/plan.tsv`, de menor a mayor | gate C por lote |
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

### 9.1 Lo caro no es el pool: es la conversación que lo orquesta

Medido el 2026-09-26, por componente, en el transcript de la sesión que
orquestó las olas 1 y 2 y en los `usage.tsv` de todas las iteraciones:

| Fuente | Unidades | cache_read | cache_creation | output |
|---|---|---|---|---|
| Conversación que orquesta | 2,904 respuestas | 1,152,885,383 | 7,151,901 | 2,711,933 |
| Pool (`claude -p`) | 696 fragmentos | 18,296,741 | 3,779,870 | 1,608,258 |

Cada respuesta de la conversación relee unos 397,000 tokens de contexto; un
fragmento traducido lee unos 26,000. Una vuelta de vigilancia («ver el log»)
cuesta lo de unos 15 fragmentos. El pool y la conversación comparten la cuota
de la cuenta, y la ola 2 la agotó a mitad del camino.

*Métrica:* tokens por componente, sumados. *Ciega a:* el peso de cada
componente en la cuota, que no está publicado aquí; por eso no se reduce a una
sola cifra.

De ahí tres reglas de operación:

- **La ola corre sola de principio a fin** y se recoge por su notificación;
  no se vigila turno a turno.
- **Contra el límite de la cuenta no hay reintento.** `translate` reconoce la
  respuesta de límite («You've hit your session limit…», que llega con
  `subtype: success`) y sale con **5**; `cycle` registra la iteración como
  `limite`, `advance` no reintenta, y la ola deja la marca `limite` para que
  los lotes que aún no arrancan salgan con 5 sin llamar al modelo. En la ola 2,
  105 de 117 rechazos eran esa respuesta, reintentada tres veces por lote.
- **Una fase larga empieza en una conversación nueva**, con el plan y el banco
  como estado: el contexto releído por respuesta es lo que se paga.

**El caché de 1 h** (`THYROX_ENABLE_PROMPT_CACHING_1H`, del proveedor) sólo
convierte escrituras en lecturas si el mismo prefijo vuelve a pedirse pasados
5 minutos. En el pool, 487 de 696 ítems escriben de 5k a 10k tokens con valores
distintos por ítem: `{ plantilla; ítem; } | claude -p` manda las dos cosas en
un mensaje, y lo escrito incluye el fragmento. Se activa en la ola 3 y se
compara por ítem contra la ola 2, en vez de suponer su efecto.

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| El verificador no ve el significado | V7 por muestreo y revisión humana de una fracción por lote |
| Texto chino incorporado en imágenes que no genera el script (capturas) | inventario por muestreo en la fase 1; sin OCR no hay medición completa |
| Una nota grande excede lo que una conversación produce de una vez (la mayor tiene 95,677 bytes) | resuelto: la unidad es el fragmento por `\section` (y por `\subsection` si pasa de 12,000 caracteres) |
| Un fragmento retraducido rompe la estructura LaTeX (cs329a, it. 04: `itemize` desbalanceado) | V0 lo rechaza al recibirlo, y `retranslate` audita los ya escritos |
| Un proceso del verificador muere y el lote parece limpio (cs329a, it. 02) | `verify:incomplete` por nota sin veredicto y salida 2; el registro lo conserva y el README del lote lo explica |
| Una fila del registro es falsa | `batches.tsv` es de solo agregar: la corrección va en la iteración siguiente y en el README del lote, nunca reescribiendo la fila |
| TikZ roto al traducir etiquetas (93 bloques) | V6 lo detecta; patrón `mechanical` si se repite |
| La memoria crece con reglas contradictorias | GATE A rechaza una señal que ya tiene patrón; una contradicción se resuelve editando la entrada, no agregando otra |

## 11. Decisiones

1. **Modelo del traductor:** `claude-sonnet-5`, sostenido por los pilotos. El
   fallo del primer intento fue del contrato, no del modelo. **Se reabre** si la
   retraducción sigue introduciendo inglés donde el original escribe chino; en
   ese caso, A/B con otro modelo sobre los mismos fragmentos, midiendo señales
   y tokens.
2. **Orden de los cursos:** decidido. Lo deriva `plan` por tamaño.
3. **Anchura:** no es una decisión. `--memfree` acota la memoria y `--width`
   solo la concurrencia contra la API (sección 2.1).
4. **Pendientes para el ejecutor:**
   - la fracción de revisión humana (V7) por lote;
   - publicar el sitio es-MX o solo construirlo;
   - «AI Agent» contra «Agentes de IA» en los títulos: si «Agent» entra al
     glosario como `keep`.
