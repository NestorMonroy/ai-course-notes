# VM ES-C — trabajador local de la traducción es-MX (lotes 31–33)

- Nodo: VM ES-C, sesión remota de Claude Code.
- Rama: `feature/es-mx-vm-c-local-worker` (ai-course-notes); en thyrox la misma, sin clon.
- Coordinador: VM ES-A (`session_011tfzc28GV3swU7BCpC5uQr`).
- Fecha: 2026-10-08T01:59Z.

## Recursos medidos

| Medida | Valor |
|---|---|
| `nproc` | 4 |
| `free -g` | 15 GB total, sin swap |
| `df -h /` | 252 GB, 21 GB disponibles (asignación de la sesión) |
| motor de contenedores | `docker` 29.8.2; **no hay `podman`** |

## Bootstrap

`VM_ES-C_BOOTSTRAP_PRISTINE = NOT RUN`. ai-course-notes está en su rama, limpio. thyrox
no se pudo adjuntar: `add_repo NestorMonroy/thyrox` (push y lectura) lo rechaza el
clasificador de permisos de la sesión (`[Permission Grant]`), dos veces. Sin clon de
thyrox no hay checklist del README, ni `bin/…`, ni Search Existing en
`origin/feature/vm-c-clean-room`.

## Materialización del 9B

`VM_ES-C_LOCAL_WORKER = BLOCKED thyrox-no-adjuntable`: sin `bin/local-models-ensure` ni
`bin/local_control_plane_ready` no hay ruta productiva. No se intentó ninguna vía fuera
de las autoridades (ni `pull` por etiqueta ni copia de GGUF). Aun con thyrox, siguen
pendientes de comprobar TASK-THYROX-1032 y 0944, y la falta de `podman` en esta VM.

## Avance por lote (trabajo determinista, sin modelo)

`translation_loop.py prepare` por lote, sin `advance` ni barrido; no toca
`translation_memory.jsonl`, `batches.tsv` ni `.last-bank`.

| Lote | Notas | Fragmentos | Traducidos | Preámbulo con `ctex` |
|---|---|---|---|---|
| 31 cs224n | 17 | 165 | 0 | no |
| 32 cs336 | 17 | 250 | 0 | no |
| 33 cs336-2026 | 19 (incluye `cs336-preamble`) | 210 | 0 | no |

## Ciega a

- No se midió nada de thyrox ni de Docker Hub desde esta VM.
- No se verificó la prosa contra `vocabulario_prohibido.txt` (vive en thyrox).
