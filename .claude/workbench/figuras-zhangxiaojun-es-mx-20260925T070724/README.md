# Cadenas de las figuras conceptuales de Zhang Xiaojun, al es-MX

`translate_figure_text.py` sobre 2,531 cadenas (`missing.txt`), en 32 lotes de
80, con anchura 10: **152 s de pared**.

| Paso | Resultado |
|---|---|
| primera corrida | 2,451 de 2,531. Un lote (el 9) volvió con una columna de número de línea delante (`16<TAB>能力风险<TAB>…`), y el filtro no lo aceptó, que es lo correcto: su primera columna no era una cadena pedida |
| `recollect.py` | se releyeron los resultados ya pagados con el parser que tolera esa sola desviación: 2,451 → 2,530 filas, sin volver a llamar al modelo |
| pendiente | 1 cadena sin traducir y la revisión `--verify` por fila del inglés introducido |

La plantilla (`figure_prompt.md`) ahora pide explícitamente no agregar columnas.
