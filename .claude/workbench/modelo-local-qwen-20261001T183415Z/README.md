# Modelo local para la traducción: instalado con thyrox y medido

Pregunta del ejecutor (2026-10-01): ¿qué modelo local se puede usar para la
traducción, instalándolo con lo que thyrox ya tiene?

## Instalación, con las herramientas de thyrox

1. `thyrox_toolchain_require_podman` (`THYROX_INSTALL_PODMAN=1`): podman
   4.9.3 (`podman-install.txt`). `bin/podman_capabilities`: run, límites de
   PIDs, CPU y memoria, red `none`, rootfs de solo lectura y propagación de
   salida y señales son efectivos en este contenedor.
2. `bin/infrastructure_ensure thyrox-ollama`: sólo Ollama; postgres y redis
   son infraestructura del propio thyrox y no hacen falta aquí
   (`ensure-ollama.txt`).
3. El primer `pull` falló por TLS: el Ollama del contenedor no confiaba en la
   CA del proxy. thyrox ya lo resuelve: con
   `THYROX_INFRA_PROXY_CA_BUNDLE=/root/.ccr/ca-bundle.crt`,
   `infrastructure_ensure` recreó el contenedor por deriva de configuración
   con la CA montada y `SSL_CERT_FILE`.
4. `ollama pull qwen2.5:7b-instruct` dentro del contenedor gestionado: 4.7 GB
   (`pull-qwen.txt`). `local-models-catalog declare` exige el modelo ya
   instalado (`declare-qwen.txt`, antes del pull).

## Medición (un fragmento real, `cs224r/lecture02/009`, 1,900 bytes)

`qwen-probe-stats.txt`, de `ollama run --verbose` con la plantilla del
traductor y el fragmento:

| Medida | Valor |
|---|---|
| lectura del prompt (1,355 tokens) | 21.36 tokens/s, 1 min 3 s |
| generación (665 tokens) | 4.10 tokens/s, 2 min 42 s |
| carga del modelo | 30 s |
| total | 4 min 16 s |

*Métrica:* `--verbose` de Ollama, una ejecución, 4 CPU sin GPU, 15 GB.
*Ciega a:* variación entre fragmentos (una muestra) y calidad según el
verificador del ciclo.

## Lectura

- Respeta los marcadores `<<<ES`/`ES>>>` y la estructura LaTeX
  (`qwen-probe-out.txt`).
- Calidad: «imitation learning» → «aprendizaje imitativo» (lo establecido es
  «aprendizaje por imitación»); deja en inglés «alignment, ops, data y legal».
- Velocidad: cs224r tiene 111 fragmentos pendientes, unas 8 horas a este
  ritmo, con la sesión activa (el contenedor se apaga al quedar inactivo).
- Dentro del pool de thyrox cada ítem pasa por `thyrox -p`, con un contexto
  de unos 126,029 tokens: a 21 tokens/s, unos 100 minutos de lectura por
  turno. Usarlo exigiría que `translate` llame a Ollama directo, con el
  fragmento dentro del prompt y sin el harness.
