# qwen-library-policy

## El encargo

<!-- verbatim, sin parafrasear -->

> si, la implementacion de MADLAD, considera usar clean-code revisa las reglas, de igual manera los nombres de archivos, clases, funciones firmas de funciones e identificadores son en ingles, los comentarios pueden ir en español pero sin coloquialismos, en donde los términos técnicos se quedan en ingles

El «si» acepta usar el Qwen 2.5 7B Q4_K_M del volumen de Ollama, con su
equivalencia al artefacto oficial sin verificar (H-THYROX-315 en thyrox).

## La premisa, si se corrigio al primer comando

El modelo ya estaba en el catálogo de thyrox desde 2026-10-01; lo que lo
excluía era la política, que sólo admitía `Qwen/Qwen2.5-7B-Instruct-GGUF`.

## Las piezas

| archivo | que hace |
|---|---|
| `probes/red.py` | la prueba de la política espera también la entrada `library/qwen2.5-7b-instruct` con `source: ollama` |
| `probes/impl.py` | añade esa entrada a `tools/lang/es-mx/model-policy.json` y lo dice en `translation_loop.py` |

## Los resultados

| Paso | Resultado | Evidencia |
|---|---|---|
| rojo | 1 falla | `outputs/red.txt` |
| verde, imagen base de thyrox | 32 pasan, 29 fallan: las que exigen hunspell/xelatex, ausentes en esa imagen | `outputs/green.txt` |
| verde, imagen del consumidor | 61/61 | `outputs/green-consumer-image.txt` |
| recomendador con la política nueva | bloquea por «sin cualificación aprobada vigente de la clase analisis entre los 1 modelo(s)»: el modelo ya es admisible y falta cualificarlo | `outputs/recommend.txt` |

El selector `source` lo aceptó thyrox en TASK-THYROX-0778.

*Metrica:* pruebas de `tests/test_translation_loop.py` en cada imagen y la causa del recomendador.
*Ciega a:* la calidad del modelo: no se ejecutó ninguna traducción.
