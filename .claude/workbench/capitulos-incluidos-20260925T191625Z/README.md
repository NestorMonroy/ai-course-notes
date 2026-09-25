# Capítulos incluidos como unidades

`self-evolving-agents-2026` incluye 9 `lectureXX-chapter.tex` con chino por
`\IfFileExists{x.tex}{\input{x.tex}}{}`. `prepare` sólo traducía la nota, y la
condición seguía mirando el capítulo zh.

## TDD

- Mitad roja: la prueba `test_included_chapters_are_translated_and_verified_as_units`
  vivía como `xfail(strict=True)` desde la ola 1; se retiró el marcador.
- Al implementar apareció un defecto no previsto: `localize` sobre un capítulo
  sin `\documentclass` aplicaba sus reglas de metadatos a la prosa (`。` → `.`),
  y el fragmento ya no casaba. Un capítulo no se localiza.
- Se agregó a la prueba que un capítulo verificado con `--compile` no da
  `compile:` (no compila solo; lo compila su nota).

## Anulación (`annul-summary.txt`)

| Mitad retirada | Aserción que cae |
|---|---|
| E: seguir los `\input` | el capítulo es-MX existe y está traducido |
| F: mapear `\IfFileExists` | la nota apunta al capítulo es-MX |
| G: compilar sólo con `\documentclass` | ningún `compile:` en el capítulo |
| H: no localizar capítulos | el capítulo es-MX está traducido |

En las cuatro, 47 pasan: ninguna otra prueba depende de estas mitades.
El arnés pasa patrón y reemplazo por `ENVIRON`: con `gawk -v` los escapes se
procesan y `\\` llegaría como `\`.
