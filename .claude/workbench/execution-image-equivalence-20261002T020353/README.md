# Equivalencia anfitrión ↔ ExecutionUnit de los verificadores es-MX (P5a/P5b)

## El encargo

<!-- verbatim, sin parafrasear -->

> y añade sólo las que son necesarias.
> Hazlo con TDD y prueba dentro de una ExecutionUnit real.
> 4. La prueba que quiero para el toolchain no es sólo “binario encontrado”
> Demuestra:
>
> ```
> ExecutionUnit
> → check_prose_vocabulary.py
> → hunspell es_MX
> → resultado correcto
> ```
>
> y:
>
> ```
> ExecutionUnit
> → XeLaTeX
> → compilación mínima representativa
> → resultado correcto
> ```
>
> Después vuelve a ejecutar las 29 pruebas que hoy fallan.
> La propiedad de cierre debe ser:
>
> ```
> baseline host
> =
> ExecutionUnit
> ```
>
> para los verificadores deterministas que deban ejecutarse en ambos entornos.
> Si alguna prueba debe seguir fuera de la unidad por diseño, documenta la razón explícita; no la dejes como diferencia accidental.
> 5. No mezcles V7 con una herramienta automatizable
> V7 sigue siendo QA visual/humana por muestreo según el plan.
> No intentes “resolver” V7 instalando otra herramienta o haciendo que Qwen se autoverifique.
> La frontera debe quedar:

## La premisa, si se corrigio al primer comando

Ninguna: el encargo se ejecutó tal como se pidió.

## Las piezas

| archivo | que hace |
|---|---|
| `outputs/` | 6 salidas: rojos, verdes y anulaciones |

## Los resultados

Identidad: `ai-course-notes:es-mx/execution-image` (referencia de trabajo del
consumidor). Proveedor: `build-image --work` (TASK-THYROX-0775).

## Toolchain derivado del call path de V0–V6 (`tools/thyrox/execution-image/Containerfile`)

| Llamado desde | Herramienta |
|---|---|
| `check_prose_vocabulary.py` | `hunspell` (diccionario del repositorio, `tools/lang/es-mx/hunspell/es_MX`) |
| `translation_loop.py` compile (V5) | `xelatex` + `NOTES_TEXLIVE_PACKAGES` de `tools/lib/toolchain.sh` |
| preámbulo localizado | FandolSong (`texlive-lang-chinese`), WenQuanYi Zen Hei (`fonts-wqy-zenhei`) |

Fuera: V7 (`render_pdf_qa.py`: pdftoppm, magick, mutool) — revisión visual por
muestreo; ninguna de las pruebas medidas es de V7. `fonts-arphic-uming` no se
añade: tampoco está en el anfitrión (la señal «AR PL UMing CN» de una nota es
igual en los dos lados).

Imagen `localhost/ai-course-notes-runner:dev`: 1.03 GB (comparte los 386 MB de
la base). Disco libre: 5.11 GB antes, mínimo 2.76 GB durante el build, 4.55 GB
después.

## Medición (`tests/test_translation_loop.py`, 61 pruebas)

| Entorno | Resultado |
|---|---|
| anfitrión, Python 3.12.3, solo | 61 aprobadas (`outputs/host-baseline.txt`) |
| unidad, imagen del consumidor, Python 3.12.3, sola | 61 aprobadas (`outputs/unit-image.txt`) |
| unidad, imagen BASE de thyrox (anulación) | 29 fallidas: `hunspell` y `xelatex` ausentes y sus cascadas (`outputs/annul-base-image.txt`) |

## Lo que la medición corrigió

1. **El `.venv` es compartido y el intérprete no estaba fijado.** El anfitrión
   usa 3.11 por defecto y la unidad 3.12; los dos cumplen `requires-python
   >=3.11`, así que cada `uv run` reconstruía el `.venv` del otro. Las dos
   primeras líneas base del anfitrión (`outputs/host-baseline-race*.txt`, 10 y
   24 fallos por `spacy-lookups-data` ausente) midieron esa carrera, no el
   toolchain. `.python-version` = 3.12 (existe en los dos) lo cierra.
2. **Anfitrión y unidad no se miden a la vez:** comparten árbol y `.venv`.
3. **Comparar fallos por nombre ocultó una regresión de P7:** una segunda
   prueba de la ola aún pasaba `--model`; fallaba antes por `hunspell` y
   después por `--model`, y la comparación por nombre la contó como la misma.
   Corregida aquí.

*Metrica:* pruebas que pasan en cada entorno y diferencias por causa.
*Ciega a:* V7, la revisión visual, que no es determinista.
