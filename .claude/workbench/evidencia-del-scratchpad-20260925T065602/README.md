# Evidencia que vivía solo en el scratchpad de la sesión

El scratchpad no se versiona. Aquí se copió lo que es **evidencia**: registros
de ejecución, mediciones, guiones de los controles de anulación y consultas a
fuentes externas. Se dejó fuera, a propósito:

- Las copias de trabajo de archivos que ya están versionados (`*.ok`, `*.mine`,
  `*.orig`, `*.fixed`, `gen.head.py`, `relabel_site.py`, `env.example.new`):
  su contenido final vive en el repositorio y su historia en git.
- Los binarios y artefactos generados: PDF, PNG, `.aux`, la copia de 13 MB del
  store de THYROX (`l6.sqlite3`), la copia de las skills instaladas y las
  salidas del sitio (`siteq/out-*`) y del árbol (`siteq/root`, 31 MB).
- El diccionario es_MX construido, que no es evidencia sino producto: vive en
  `tools/lang/es-mx/hunspell/`.

## Índice

| Archivo | Qué mide |
|---|---|
| `courses.tsv` | los 35 cursos por tamaño en bytes y número de notas; es el orden de la fase 3 |
| `fig_missing.txt` | las 2,531 cadenas con chino de las figuras conceptuales que faltan en `figure_text.tsv` |
| `annul*.sh`, `annul/` | los guiones de los controles de anulación de esta sesión |
| `apt-hunspell.log` | la instalación de `hunspell` y `hunspell-es` |
| `rla-es-comparacion/conteos.txt` | 59,411 entradas del es_MX construido desde RLA-ES (`fb279606`) contra 57,157 del paquete de Debian |
| `lecture02-notes.es-mx.log` | la compilación de cs329a/lecture02 con el `\enquote` sin definir (fase 2) |
| `iate.json`, `fundeu.html` | consultas a IATE y a FundéuRAE para el glosario |
| `siteq/compare.sh`, `siteq/diff.txt` | la comparación del sitio zh antes y después de `--lang`: `diff.txt` vacío, idéntico byte a byte |
| `zh-equiv/` | la equivalencia byte a byte de los guiones de QA en las 370 notas zh |
| `tpl/` | la compilación de la plantilla es-MX |
| `test-*.log`, `red*.log`, `derived*`, `tc-*` | ejecuciones de pruebas de THYROX y de este consumer, con sus mitades rojas |
