# Procedencia de `tools/lang/es-mx/` y de `check_prose_vocabulary.py`

Copiado y adaptado de THYROX para que este repositorio no dependa de él al
revisar la prosa en español.

| Aquí | Origen en THYROX (`792af5f29`) | Cambio |
|---|---|---|
| `prohibited_forms.txt` (líneas 1–129) | `src/verify/vocabulario_prohibido.txt` | copia byte a byte |
| `prohibited_forms.txt` (resto) | — | propio: spanglish que el eje morfológico no ve |
| `prose_vocabulary_baseline.txt` | — | propio: vacío, la prosa es-MX empieza sin deuda |
| `glossary.tsv` | — | propio: términos técnicos y formas rechazadas |
| `tools/scripts/check_prose_vocabulary.py` | `src/verify/check_vocabulario_prosa.py` | ejes `inventado` y `prohibido`, `attested()`, frontera de palabra y rechazo sin cifra; exenciones de LaTeX en vez de RST; ejes `spanglish` y `english` nuevos |
| eje `english` | `spanish_by_corpus()` de `src/verify/check_identifier_language.py` | su inverso, con el mismo margen de 3.0 |

Una corrección que se haga en THYROX no llega sola: se revisa este archivo y se
porta a mano, dejando aquí el nuevo commit de origen.
