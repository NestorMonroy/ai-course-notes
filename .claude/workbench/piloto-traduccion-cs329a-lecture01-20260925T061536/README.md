# Piloto cs329a/lecture01, primer intento: no escribió ningún fragmento

Corrida del 2026-09-25 con `translation_loop.py translate --model claude-sonnet-5`,
10 fragmentos y anchura 12 (derivada al lanzar; ese cálculo se retiró después).
Los 10 items terminaron y **ninguno escribió su fragmento**. El `pkill` con el
que se intentó detenerlos casó con la línea de comando de su propio shell
(`[_]headless_item` aparecía literal en otro patrón del mismo comando) y mató a
ese shell, no al pool: es la forma de `H-THYROX-103`.

## Qué se midió

| Defecto | Evidencia |
|---|---|
| `claude -p` bloquea `Write` bajo `.claude/` por ser una ruta sensible | `translate/*/2.json`, `7.json`, `8.json`, `9.json`, `10.json`: el `result` pide aprobar la escritura |
| `headless-pool` parte `index.tsv` con `--colsep '\t'` y pasa `{1} {2}`: la segunda ruta del item `zh<TAB>es` no llegaba al modelo | `translate/*/index.tsv` tiene tres columnas |
| El fragmento 000 (la portada, ya localizada por script) no tiene chino y aun así pagó una conversación | `1.json`: «no contiene texto en chino que traducir» |

## Tokens por componente

| | input | cache_creation | cache_read | output |
|---|---:|---:|---:|---:|
| total, 10 items | 80 | 90,414 | 375,637 | 37,784 |

Piso por item: ~24,000 `cache_read` y ~6,000 `cache_creation` antes de
traducir. En los items 3 a 6 el modelo devolvió la traducción en su respuesta al
no poder escribirla: ~7,000 `output` por fragmento de 3.4 a 5.3 KB.

*Métrica:* `usage` de la salida `--output-format json` de cada item.
*Ciega a:* la llamada de prueba previa (`claude -p` con «OK»), que no pasó por el pool.

## Qué cambió por esto

Commit `11e2e81`: el modelo solo lee (`--tools Read`) y devuelve el fragmento
entre `<<<ES` y `ES>>>`, y el ciclo lo escribe. El item es una sola ruta. Los
fragmentos sin chino se copian. La memoria se acota con `--memfree`. El segundo
intento vive en el banco hermano con la marca de tiempo siguiente.
