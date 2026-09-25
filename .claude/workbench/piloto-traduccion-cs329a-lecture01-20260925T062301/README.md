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
