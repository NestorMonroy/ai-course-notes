# El traductor es-MX pasa al ejecutor de THYROX con Qwen (trabajo del consumidor)

Identidad: `ai-course-notes:es-mx/executor-qwen` (referencia de trabajo del
consumidor, TASK-THYROX-0756); no es una TASK de THYROX. Sólo cambia el punto
de ejecución de `ES_MX_TRANSLATION_PLAN.md`; glosario, memoria, prompt,
marcadores, V0–V7, triage, sweep, retranslate y measure no se tocan.

- `translate`/`advance`/`cycle` y `translate_wave.sh` dejan de aceptar
  `--model`. `translate` pide a `headless-pool`: `--execution unit`,
  `--work-reference ai-course-notes:es-mx/<lote>/translate/<sello>`,
  `--model-policy tools/lang/es-mx/model-policy.json` y `--task-class analisis`.
- `tools/lang/es-mx/model-policy.json`: sólo `Qwen/Qwen2.5-7B-Instruct-GGUF`
  Q4_K_M, `fallback.enabled: false`. Sin la política, `translate` sale 2.
- Plan §3 (fila Agente), §6 (orden de la ola) y §11.1 (modelo): actualizados.

Medición en ExecutionUnit: la imagen de ejecución no trae `hunspell` ni
`xelatex`, así que 29 pruebas del ciclo fallan igual antes y después
(`outputs/baseline-unit.txt`, `outputs/green-final.txt`; la comparación de
conjuntos está en la salida del commit). Las nuevas y la de la ola: verdes.

| Anulación | Cae |
|---|---|
| `--execution unit` | «asks the pool for units under the consumer policy» |
| política legible obligatoria | «refuses without a readable policy» |

Mitad roja: `outputs/red.txt` (46 fallos: `--model` obligatorio).
