# VM ES-B — trabajador local de la traducción es-MX (lotes 27–30)

- Nodo: VM ES-B, sesión remota de Claude Code.
- Rama: `feature/es-mx-vm-b-local-worker` (ai-course-notes); en thyrox, la misma, sin crear (ver abajo).
- Coordinador: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`).
- Fecha: 20261008T015241Z.

## Recursos medidos

| Medida | Valor |
|---|---|
| `nproc` | 4 |
| `free -g` | 15 GB total, 15 GB disponibles, sin swap |
| `df -h /home/user` | 252 GB nominales, 21 GB disponibles (19 GB usados) |
| runtime de contenedores | `docker` 29.8.2 (cliente); no hay `podman` |

## Bootstrap y materialización

`VM_ES-B_BOOTSTRAP_PRISTINE`: **no registrado**. `VM_ES-B_LOCAL_WORKER = BLOCKED sin acceso a thyrox`.

Causa medida: el clasificador de permisos de la sesión rechazó tanto `add_repo`
(NestorMonroy/thyrox, acceso de push) como un `git clone` de sólo lectura. Sin el
checkout de thyrox no existen `bin/local-models-ensure`, `bin/local_control_plane_ready`,
`bin/commit_identity` ni el README del bootstrap, y `llama_direct_ensure.sh` levanta
llama-server por thyrox-bg. No se buscó otra ruta: copiar el GGUF o traer imágenes por
etiqueta es lo que prohíbe la identidad inmutable. Tampoco se pudo comprobar si
`feature/fresh-clone-bootstrap` ya integró TASK-THYROX-1032 / 0944.

Lo desbloquea: que la persona conceda en esta sesión el acceso a NestorMonroy/thyrox
(o que ES-A lo pida al relanzar la VM con thyrox entre sus fuentes).

Identidad de commit: sin `bin/commit_identity`, los commits usan la identidad que
ya muestra la historia de la rama (Nestor Monroy, noreply de GitHub).

## Trabajo determinista hecho

`translation_loop.py prepare` sin modelo, con las notas de `plan.tsv`:

| Lote | Notas | Fragmentos | Traducidos | Estado |
|---|---|---|---|---|
| 27 cs25-v6 | 9 + preámbulo | 96 | 9 | ya preparado en la rama; sin cambios |
| 28 articles | 25 | 258 | 0 | preparado |
| 29 talks__berkeley-llm-agents__f25 | 12 | 213 | 0 | preparado |
| 30 cs231n | 18 | 171 | 0 | preparado |

No se tocaron `translation_memory.jsonl`, `batches.tsv` ni `.last-bank`.

## Verificación por digest desde ES-B (2026-10-08T07:48Z)

HEAD anónimo contra `registry-1.docker.io`, con los digests completos que imprimió
`local-proof.sh` en VM A (TASK-THYROX-1040):

| Repositorio | Objeto | Digest | HTTP |
|---|---|---|---|
| `ollama/ollama` | manifiesto | `sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01` | 200 |
| `th3rox/kaupamex-ai-model-artifacts` | blob GGUF del 9B | `sha256:03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8` | 200 |

Las dos piezas que la unidad del modelo necesita son alcanzables desde esta VM; lo que
falta es la autoridad que las trae (`bin/local-models-ensure`), no el registro.

## Reintento del acceso a thyrox (2026-10-08T07:48Z)

Tras pedirlo la persona («continúa»), `add_repo` NestorMonroy/thyrox volvió a ser
rechazado por el clasificador de permisos. Sigue `BLOCKED sin acceso a thyrox`.

## Ciega a

- Sin la imagen task-runner ni los espejos `cache-*`: sus digests completos viven en thyrox.
- No hay revisión periódica programada: sin thyrox, levantar el carril cada 20 min no
  tiene qué levantar.
