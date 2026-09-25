# Piloto cs329a/lecture01, segundo intento

`translation_loop.py translate --model claude-sonnet-5` con el contrato de
`11e2e81`: el modelo lee el fragmento y devuelve la traducción entre marcadores.
Hubo 9 fragmentos al modelo y 1 copiado (la portada no tiene chino). Anchura
10, `--memfree 3G`, **30 s de pared**, 9 de 9 con marcadores y 2 turnos cada uno.

## Tokens por componente (`usage.tsv`)

| | input | cache_creation | cache_read | output |
|---|---:|---:|---:|---:|
| total, 9 items | 36 | 47,677 | 125,110 | 16,077 |

El piso por item bajó de ~24,000 a ~13,400 `cache_read`, porque leer y
responder toma 2 turnos en lugar de 3 a 8. Letras del es-MX por carácter Han:
**5.49** sobre los fragmentos. *Ciega a:* las letras de los comandos de LaTeX,
que también cuentan, así que no es todavía el factor de prosa (4.38) del perfil.

## Verificación

- `signals-1.jsonl`: 59 señales. Todas de prosa y ninguna de paridad, cobertura
  ni compilación. 53 eran inglés que la nota zh ya escribe (términos técnicos,
  opciones de tcolorbox), así que el verificador marcaba el significante y no el
  significado. Se corrigió: solo es defecto el inglés que introdujo la
  traducción.
- `signals-2.jsonl`: quedan 6 señales:
  - `preentrenamiento` y `observabilidad`: formas españolas que el léxico no
    trae y que van al glosario con su fuente;
  - `iterable`, `prompts`, `prompting` y `workers`: inflexiones de términos del
    original o calcos que hay que revisar.

  Esto es la entrada de la memoria y del GATE A.

## Revisión visual y lo que destapó

1. **Un PDF truncado se aceptaba.** El primer PDF tenía 16 páginas con
   XeLaTeX saliendo con 1: una coma española partía la clave `title=#1` de
   una caja (838 definiciones en 275 archivos). `verify --compile` lo daba por
   bueno porque existía el PDF. Se corrigió en `813c624`: los títulos van entre
   llaves y el veredicto sale de las líneas `! ` del log. Con eso el PDF tiene
   22 páginas y 0 errores (`qa/contact-sheet.png`).
2. **Faltaban palabras en la portada.** El título de la portada decía «AI Agent /
   Part 1:». El chino de `\notetitle` sobrevivía en el preámbulo y la fuente
   latina lo omitía con un aviso (`Missing character`, 11 en el log). Se corrigió
   en `b722031`: el preámbulo con chino es una unidad más del traductor,
   `residual-han` cubre el documento entero y el glifo faltante es una señal.
3. **Esperas que no terminaban.** Dos esperas de esta revisión giraron más de 6
   minutos sin salida. Buscaban un número en la última línea del `.output` del
   cliente, y el cliente agrega ahí `[exited with code N]` al terminar, así que
   la condición no podía cumplirse. La compilación había terminado bien. Una
   espera se recoge con la notificación del cliente o con `thyrox-bg`/`wait-jobs`,
   nunca con un patrón sobre un archivo que escribe otro.

La cabecera se tradujo como unidad propia (`translate-head.log`, 1 de 1) y la
nota verifica con 0 señales, glifos incluidos (`signals-5.jsonl`).
**Pendiente para V7:** el original escribe «AI Agent» en inglés y la
traducción del título dice «Agentes de IA». Queda para la revisión humana si
«Agent» entra al glosario como `keep`.
