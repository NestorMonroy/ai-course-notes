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

## Diccionario hunspell es_MX (`hunspell/`)

Construido desde las fuentes de RLA-ES (Recursos Lingüísticos Abiertos del
Español), el proyecto de Santiago Bosio e Ismael Olea que alimenta los
diccionarios de LibreOffice, Apache OpenOffice y Firefox. Licencia triple
(GPL-3+, LGPL-3+ o MPL-1.1+); el texto está en `hunspell/LICENSE-RLA-ES.md`.

| Aquí | Origen | Cómo |
|---|---|---|
| `hunspell/es_MX.dic` (59,411 entradas), `hunspell/es_MX.aff` | `NestorMonroy/rla-es` en `fb279606e9ad229b9d892b0344fbb8d4ee8c47ca` (2026-09-19) | `bash tools/lang/build_hunspell_dictionary.sh <checkout> es_MX tools/lang/es-mx/hunspell` |
| `tools/lang/build_hunspell_dictionary.sh` | `herramientas/make_dict.sh` y `herramientas/remover_comentarios.sh` | los pasos de construcción de una localización, sin las preguntas de publicación |

*Por qué no el paquete `hunspell-es` de Debian:* es el mismo proyecto
(`dictionaries/es/*` de LibreOffice 24.2.1, atribuido a Santiago Bosio), pero
con 57,157 entradas. Además, la descarga directa de las versiones de RLA-ES en
GitHub responde 403 desde el contenedor. Construirlo aquí lo fija a un commit
y quita la dependencia de apt; del sistema solo hace falta el binario
`hunspell`.

*Métrica:* pertenencia de una forma al español de México según las listas de
la RAE y las no RAE de RLA-ES para es_MX. *Ciega a:* las derivaciones técnicas
(`observabilidad`, `preentrenamiento`, `tokenización`, `escalabilidad`), que
van al glosario con su fuente y son candidatas a proponerse al fork en
`ortografia/palabras/noRAE/`.
