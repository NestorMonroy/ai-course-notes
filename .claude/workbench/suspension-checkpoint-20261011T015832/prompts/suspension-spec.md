# THYROX — Suspensión controlada, preservación integral y reanudación reproducible

Texto del ejecutor, 2026-10-11 ~01:55Z, recibido por ES-A
(session_011tfzc28GV3swU7BCpC5uQr). Precedido de: «en el repositorio de thyrox
vas a integrar todo el trabajo que se esta haciendo en
feature/fresh-clone-bootstrap a nuestra rama de trabajo, posterior,». Las
viñetas se conservan como listas.

## 1. Objetivo obligatorio

Ejecuta un procedimiento de suspensión controlada y preservación integral del estado actual de Thyrox, incluyendo todos los nodos y máquinas virtuales que puedan identificarse mediante las autoridades existentes.

El objetivo es permitir que el proyecto se reanude dentro de varios días, incluso si quien lo retoma es otro operador, otra sesión de coordinación o un modelo diferente.

La reanudación debe recuperar el trabajo realmente pendiente sin reconstruir innecesariamente el contexto, repetir investigaciones completadas, duplicar TASKs, reconstruir imágenes existentes ni consumir nuevamente los recursos de inferencia utilizados para desarrollar los planes actuales.

Esta instrucción autoriza preparar y ejecutar el cierre controlado del trabajo actual. No autoriza eliminar artefactos, perder cambios, sobrescribir trabajo ajeno ni sustituir el objetivo persistente de Thyrox.

El objetivo padre continúa siendo la autonomía local de extremo a extremo, utilizando únicamente modelos generativos locales.

Restricciones fundamentales

1. No asumir qué TASK está ejecutándose.
2. No asumir cuántas VMs existen o están activas.
3. No asumir cuál es la rama principal de trabajo.
4. No asumir que todos los procesos pertenecen a una misma sesión.
5. No asumir que un PID registrado sigue representando al proceso original.
6. No asumir que todos los artefactos están versionados.
7. No asumir que Docker Hub contiene las imágenes locales.
8. No asumir que un `RepoDigest` demuestra disponibilidad remota.
9. No asumir que una TASK marcada como completada está integrada.
10. No asumir que el coordinador actual volverá a utilizarse.

Descubre el estado real mediante los mecanismos existentes y registra explícitamente aquello que no pueda verificarse.

## 2. Semántica de la operación

La operación solicitada es una suspensión administrativa recuperable, no un reinicio de la infraestructura.

Debe distinguir tres acciones:

QUIESCE / DRAIN — Impedir nuevas asignaciones y permitir que los trabajos admitidos alcancen un punto seguro de conservación.

CHECKPOINT / PRESERVE — Guardar código, progreso, estado de ejecución, artefactos, decisiones, dependencias, evidencia y mecanismos de recuperación.

STOP / CANCEL — Detener mediante las autoridades correspondientes aquello que pueda suspenderse o cancelarse sin pérdida de información exclusiva.

No emplear cancelación indiscriminada de procesos.

No utilizar `kill -9`, `pkill`, `podman system prune`, `podman image prune`, `git reset --hard`, `git clean -fdx` ni operaciones equivalentes que destruyan estado sin clasificación y autorización individual.

Si una unidad carece de capacidad de checkpoint o cancelación segura, conservar su estado, identificar su propietario y aplicar el mecanismo de detención admitido por su contrato.

Si no puede demostrarse una detención segura, registrar el bloqueo y preservar la ejecución en lugar de forzar su terminación.

El cierre deberá distinguir entre:

- Trabajo terminado y asentado.
- Trabajo ejecutándose que pudo finalizar durante el drenaje.
- Trabajo interrumpido con estado recuperable.
- Trabajo bloqueado.
- Trabajo cuyo estado no pudo verificarse.
- Trabajo con un propietario inaccesible.

Reutilizar los estados existentes; estos conceptos no obligan a crear un nuevo modelo público de estados.

## 3. Descubrimiento completo del estado actual

Antes de detener cualquier servicio o cancelar una ejecución, descubre las autoridades y sus registros.

No comiences con identificadores de TASK proporcionados manualmente.

### 3.1. Repositorio y ramas

Identifica:

- Repositorio canónico y URL remota.
- Commit actual y rama activa.
- Ramas locales.
- Ramas remotas.
- Worktrees registrados.
- Worktrees pertenecientes a ejecuciones activas.
- Worktrees con archivos modificados.
- Archivos untracked.
- Archivos ignorados con posible evidencia exclusiva.
- Commits locales pendientes de push.
- Commits publicados.
- Divergencias entre ramas.
- Operaciones Git incompletas.
- Cambios todavía no integrados.
- Dependencias entre ramas.
- Cambios relacionados con la transición hacia `kaupamex-ai`.

No fusionar todas las ramas como parte del cierre.

No asumir que las ramas con fechas recientes contienen trabajo aceptado.

No eliminar ni recrear worktrees durante el descubrimiento.

Conservar una relación verificable entre rama, commit, propietario, TASK, trabajo pendiente y evidencia.

### 3.2. TASKs y planificación

Consultar las autoridades existentes de:

- `agent_store`
- `execution-records`
- `local_plan`
- `task_source`
- `implementation_order`
- `continuation_frontier`
- `node_next_task`
- `task_continuation`
- Los mecanismos de coordinación y colas.

Descubrir todos los identificadores vigentes a partir del estado real.

No crear TASKs duplicadas porque una ejecución esté incompleta o una VM no responda.

Para cada TASK relevante conservar:

- Identificador real.
- Objetivo.
- Estado actual.
- Rama y commit.
- Propietario.
- Nodo asignado, si existe.
- Dependencias.
- Prioridad vigente.
- Intento de ejecución.
- Modelo requerido y modelo realmente utilizado, cuando se pueda verificar.
- Resultado del último intento.
- Cambios producidos.
- Verificaciones efectuadas.
- Evidencia de aceptación.
- Estado de integración.
- Causa de bloqueo, si existe.
- Punto de continuación.
- Próxima acción admisible.

Distinguir explícitamente entre una TASK terminada, verificada, aceptada e integrada.

No marcar una TASK como completada únicamente porque el proceso terminó.

### 3.3. Máquinas virtuales y nodos

Descubrir los nodos mediante los mecanismos de coordinación, los registros de ownership, las sesiones y las fuentes de infraestructura actualmente autorizadas.

No utilizar una lista fija de VM A, VM B, VM C, etc.

Para cada nodo identificado conservar:

- Identidad estable del nodo.
- Identificador de instancia, si existe.
- Estado observado.
- Última comunicación comprobada.
- Rama y commit disponibles.
- TASKs asignadas.
- Procesos activos.
- Contenedores administrados.
- Modelos locales disponibles.
- Artefactos OCI locales.
- Espacio de almacenamiento.
- Dependencias externas necesarias.
- Evidencia pendiente de publicar.
- Capacidad de recuperación.
- Estado de suspensión alcanzado.

No equiparar una rama remota con una VM operativa.

Un nodo inaccesible debe permanecer clasificado como no verificado, no como vacío o terminado.

Cuando haya VMs efímeras, identificar qué información desaparecería al detener la máquina.

Preservar primero los datos durables y la evidencia exclusiva.

No destruir ni reemplazar VMs para completar el inventario.

### 3.4. Procesos, jobs y agentes

Reutilizar:

- `wait-jobs`
- `thyrox-bg`
- `headless-pool`
- `model_coordinator`
- Los mecanismos existentes de supervisión, registro, ownership y cancelación.

Descubrir procesos y ejecuciones activos sin depender exclusivamente de los PID files.

Correlacionar, cuando corresponda:

- PID y tiempo de inicio.
- Proceso propietario.
- Árbol de procesos.
- ExecutionUnit.
- TASK.
- Rama y worktree.
- Logs.
- Writers activos.
- Leases.
- Contenedores.
- Estado de verificadores.
- Recursos asignados.
- Progreso verificable.

No considerar que `kill -0` demuestra progreso real.

No considerar que un proceso en estado sleeping está necesariamente bloqueado.

No concluir que un job terminó únicamente porque desapareció su proceso.

Identificar procesos zombie, estados obsoletos y registros incompletos sin alterar inmediatamente el estado.

Conservar las salidas y eventos de terminación mediante sus mecanismos habituales.

## 4. Establecer una barrera de suspensión

Una vez identificadas las autoridades, establecer una barrera de admisión que impida nuevas asignaciones de trabajo.

Utilizar las capacidades existentes del planificador, coordinador y runtime.

No desarrollar otro scheduler ni una cola alternativa.

La barrera debe impedir:

- Nuevas TASKs iniciadas automáticamente.
- Nuevas asignaciones a workers.
- Nuevos intentos de implementación.
- Reintentos automáticos innecesarios.
- Creación de VMs para ampliar capacidad.
- Reconstrucciones de imágenes que no sean necesarias para preservar estado.
- Nuevas descargas de modelos que no sean necesarias para recuperar evidencia.

La barrera no debe bloquear operaciones de preservación como:

- Asentar resultados.
- Finalizar una verificación activa.
- Guardar un checkpoint.
- Publicar una imagen elegible.
- Confirmar un manifest remoto.
- Publicar commits.
- Guardar registros.
- Cerrar correctamente recursos.

Registrar el alcance de la barrera y sus límites.

Si existe una operación que puede admitir trabajo sin pasar por la barrera, clasificarla como riesgo residual y aplicar el mecanismo autorizado que corresponda.

No declarar que el sistema está en drenaje hasta verificar que las rutas pertinentes dejaron de admitir nuevas ejecuciones.

## 5. Drenaje de ejecuciones activas

Aplicar el drenaje conforme al contrato de cada tipo de ejecución.

Trabajo próximo a finalizar — Permitir la finalización si puede comprobarse que progresa y su terminación segura es preferible a una cancelación. No ampliar indefinidamente el drenaje.

Trabajo de larga duración — Identificar si el runtime ofrece checkpoint, cancelación cooperativa o persistencia de resultados parciales. Solicitar primero el mecanismo cooperativo disponible. Guardar la salida parcial y su estado verificable.

Trabajo generativo local — Preservar:

- Prompt o instrucción efectiva.
- TASK y objetivo.
- Identidad del modelo.
- Configuración de runtime.
- Herramientas autorizadas.
- Cambios escritos.
- Salidas parciales.
- Verificaciones ejecutadas.
- Razón exacta de interrupción.

No asumir que puede reanudarse la inferencia exactamente desde el último token.

Si el runtime no ofrece restauración exacta de su estado interno, registrar que la reanudación será desde un checkpoint lógico del trabajo y no desde el estado computacional de inferencia.

Trabajo de integración — No interrumpir una integración en medio de una operación que pueda dejar inconsistencias. Permitir la finalización segura o utilizar el mecanismo transaccional o de recuperación existente.

Trabajo bloqueado — No consumir recursos intentando resolver indefinidamente el bloqueo durante el cierre. Registrar el problema, la evidencia disponible y la próxima acción necesaria.

El propósito del drenaje es obtener un estado consistente, no completar todo el proyecto antes de suspenderlo.

## 6. Preservación integral de Git y worktrees

No considerar que `git push` conserva automáticamente todos los archivos de una ejecución.

Antes de modificar un worktree, inspeccionar:

- Cambios staged.
- Cambios unstaged.
- Archivos untracked.
- Archivos ignorados con evidencia relevante.
- Cambios en submódulos.
- Metadatos Git necesarios para recuperación.
- Operaciones de merge, cherry-pick o rebase incompletas.
- Logs abiertos.
- Archivos con writers activos.

Preservar todos los cambios recuperables mediante las autoridades y políticas existentes.

Los cambios completos y verificados deben seguir su flujo normal de commit y publicación.

Los cambios parciales que todavía no son aceptables no deben presentarse como implementaciones terminadas.

Conservarlos como trabajo recuperable mediante mecanismos durables aprobados, con referencia al commit base, rama, TASK, propietario y evidencia de su contenido.

No crear commits ficticios de implementación aceptada.

No ejecutar `git stash` indiscriminadamente, porque puede omitir archivos no rastreados y crear una referencia difícil de recuperar por otra sesión.

No versionar secretos, caches desechables, archivos `oom` generados por el runtime ni logs con writers activos de forma prematura.

No sobrescribir archivos de otro worktree para consolidar cambios.

No fusionar ramas sin verificación.

Registrar cuáles cambios fueron publicados y cuáles quedaron preservados localmente por una razón justificada.

## 7. Preservación de imágenes Podman y Docker Hub

Este apartado es obligatorio antes de apagar cualquier VM cuyo almacenamiento pueda perderse.

Reutilizar:

- `@thyrox/image-registry`
- `@thyrox/artifact-registry`
- `@thyrox/podman-execution`
- `@thyrox/model-artifacts`
- Las operaciones existentes de observación, publicación, promoción y recuperación OCI.

Respetar ADR-007.

### 7.1. Inventario

Para cada imagen local relevante identificar:

- Image ID completo.
- Repository y tags.
- RepoDigests.
- Identidad de contenido.
- Definición de construcción.
- Commit de procedencia.
- Lifecycle.
- Owner.
- TASK relacionada.
- Contenedores consumidores.
- Dependencias de otros componentes.
- Evidencia exclusiva.
- Tamaño aparente.
- Bytes exclusivos recuperables, si pueden medirse.
- Destino OCI declarado.
- Estado de publicación.
- Manifest remoto verificado.
- Recuperabilidad.
- Estado de preservación.

Incluir imágenes sin etiqueta.

No asumir que una imagen `untagged` está abandonada.

No confundir un digest de manifest OCI con un identificador local de imagen ni con el SHA-256 de un GGUF.

### 7.2. Publicación de imágenes propias

Identificar las imágenes que deban preservarse o distribuirse mediante Docker Hub u otro registry autorizado.

Publicar solamente las que cumplan los criterios vigentes de procedencia, validación, seguridad y lifecycle.

No publicar automáticamente todas las imágenes locales.

Antes de publicar, comprobar credenciales, autorización y ausencia de información sensible conforme a la política de Thyrox.

No utilizar un modelo generativo para realizar directamente operaciones privilegiadas de publicación.

Utilizar los mecanismos deterministas existentes.

Si una imagen ya existe remotamente con identidad verificada, evitar publicaciones duplicadas.

Si requiere publicación y es elegible, efectuarla mediante la autoridad OCI existente.

Después de publicar, verificar el manifest y digest remotos.

Registrar la identidad inmutable de recuperación.

No considerar un `push` exitoso como única prueba de preservación.

### 7.3. Credenciales de Docker Hub

Respetar la separación entre lector y publisher.

Consultar el contrato vigente de `readerCredential.ts`.

Utilizar `THYROX_REGISTRY_READER_USERNAME` y `THYROX_REGISTRY_READER_TOKEN` para la lectura autenticada cuando estén declaradas y admitidas.

Verificar por código si `THYROX_REGISTRY_READER_WRITE_TOKEN` tiene consumidores reales. No asumir que pertenece al contrato de lectura o publicación.

Examinar los mecanismos vigentes de publisher y sus credenciales reconocidas.

No usar automáticamente `DOCKER_PAT_RW` como token de lectura.

No imprimir valores de credenciales.

No incluir tokens en los paquetes de recuperación.

El checkpoint debe documentar los nombres de variables y los permisos requeridos, sin almacenar sus valores.

Si no existen credenciales válidas, conservar la imagen local y registrar el bloqueo de publicación.

### 7.4. Prohibición de eliminación insegura

No ejecutar operaciones masivas de limpieza.

No eliminar una imagen protegida simplemente porque posee `RepoDigests`.

No considerar una imagen publicada si no hay evidencia suficiente del contenido remoto.

No eliminar imágenes con consumidores activos, evidencia exclusiva o lifecycle desconocido.

Comprobar que las rutas de eliminación existentes apliquen la política de preservación.

No introducir una ruta nueva que eluda las autoridades de Thyrox.

Durante este cierre, el objetivo es preservar, no recuperar espacio mediante eliminación agresiva.

Si no se puede publicar una imagen, no eliminarla.

### 7.5. Estado del almacenamiento Podman

Registrar:

- Versión de Podman.
- Backend de almacenamiento.
- Estado de bloqueos.
- Imágenes.
- Contenedores.
- Pods.
- Volúmenes.
- Recursos persistentes.
- Estados aparentemente obsoletos.
- Errores de recuperación identificados.

Utilizar observación de solo lectura para el inventario.

No modificar directamente el almacenamiento interno.

No eliminar volúmenes como consecuencia de detener un contenedor.

Un contenedor detenido no implica que su volumen sea innecesario.

Preservar los datos y referencias que permitan reactivar los contenedores mediante la autoridad gestionada.

## 8. Modelos locales, datasets y artefactos

Descubrir el catálogo real de modelos presentes.

No asumir que únicamente existe Qwen3.5-9B u otro modelo mencionado históricamente.

Para cada modelo relevante registrar:

- Identidad.
- Arquitectura y versión.
- Formato y cuantización.
- Hash del artefacto.
- Ruta o ubicación durable.
- Origen.
- Runtime compatible.
- Configuración validada.
- Requisitos de CPU, RAM y contexto.
- Cualificaciones aprobadas.
- Cualificaciones fallidas.
- TASKs consumidoras.
- Estado de residencia.
- Estado de preservación y recuperación.

Conservar los registros de cualificación independientemente de los pesos.

No eliminar artefactos GGUF para liberar almacenamiento sin demostrar previamente su recuperación.

No asumir que un volumen de Ollama es la fuente autoritativa.

Identificar las copias locales y remotas durables.

No volver a descargar un modelo si existe una copia válida y verificada.

Conservar los datasets, índices, metadatos y manifiestos necesarios para continuar las tareas pendientes.

Distinguir entre artefactos reproducibles y fuentes exclusivas.

Preservar la configuración real de inferencia y las versiones de los binarios utilizadas.

No inventar parámetros de lanzamiento de modelos.

Reutilizar el catálogo, las cualificaciones y los mecanismos de runtime administrado.

## 9. Estados persistentes y bases de datos

Identificar las bases de datos y almacenes utilizados por Thyrox.

Incluye, según existan en el estado actual:

- `agent_store`.
- `execution-records`.
- PostgreSQL.
- `SemanticSearchStore`.
- Catálogos de modelos.
- Catálogos de artefactos.
- Registros de cualificación.
- Planificación persistente.
- Colas.
- Mailboxes.
- Registros de coordinación.
- Estados de ejecución.
- Evidencia de verificadores.

No asumir que Redis o cualquier caché contienen la única copia durable del estado.

Determinar las fuentes autoritativas.

Utilizar los procedimientos existentes de snapshot, backup, flush, checkpoint o exportación consistente.

No copiar directamente una base de datos activa si su formato y modo de operación no garantizan una copia consistente.

Si se necesita detener un servicio para obtener un respaldo consistente, hacerlo conforme a su contrato y después de drenar a sus consumidores.

Conservar esquema, versión, migraciones, identidad de la base y evidencia de integridad.

No almacenar contraseñas en manifiestos de suspensión.

Verificar que los registros preservados puedan abrirse o restaurarse mediante un procedimiento no destructivo.

## 10. Contexto y decisiones para otro coordinador

No confiar en que la nueva sesión tendrá el historial de conversación actual.

Crear o actualizar un punto de entrada documental durable dentro de los mecanismos de documentación y workbench existentes.

No inventar otra jerarquía de carpetas si Thyrox ya tiene una ubicación designada para handoff, checkpoint o recuperación.

Identificar el archivo canónico mediante búsqueda de los contratos existentes.

El documento de recuperación debe explicar:

Objetivo principal — Qué intenta conseguir Thyrox y cuáles son sus criterios de aceptación.

Arquitectura vigente — Qué componentes son autoridades y cuáles son consumidores. No reconstruir toda la arquitectura en el documento; referenciar la versión vigente y los contratos verificables.

Decisiones que no deben reabrirse innecesariamente — Incluir las decisiones arquitectónicas y operativas verificables, especialmente:

- Autoimplementación con modelos locales.
- Uso de Podman conforme a ADR-007.
- Uso de autoridades existentes.
- Preservación OCI antes de eliminación.
- Separación de imágenes y pesos GGUF.
- Separación de credenciales de lectura y publicación.
- Migración gradual de Thyrox hacia Kaupamex.
- Conservación de identificadores históricos.
- Integración mediante pruebas y evidencia.
- Concurrencia sujeta a admisión y ownership.
- No usar Claude como fallback generativo.

Referenciar los ADR y documentos originales.

No convertir en decisiones definitivas recomendaciones que aún no fueron aprobadas.

Trabajo realizado — Relacionar cambios aceptados, commits, pruebas y resultados.

Trabajo pendiente — Relacionar TASKs reales, dependencias, responsables, bloqueos y próximos pasos.

Trabajo interrumpido — Identificar el punto desde el cual puede reanudarse sin volver a realizar análisis previos.

Hallazgos — Conservar identificadores, estado y evidencia. No presentar hallazgos históricos resueltos como fallos actuales.

Incertidumbres — Registrar lo que no pudo comprobarse. No completar datos desconocidos mediante inferencias.

Próxima acción — Explicar cómo Thyrox debe seleccionar la siguiente TASK mediante sus mecanismos existentes. No codificar manualmente una TASK concreta como siguiente paso obligatorio.

## 11. Reducción del costo de contexto

La reanudación debe evitar releer transcripts completos y volver a ejecutar investigaciones ya realizadas.

Para ello, reutilizar las capacidades existentes de gestión y compresión de contexto, incluyendo `@thyrox/context-compression` cuando corresponda.

El paquete de recuperación debe separar:

- Resumen ejecutivo de reanudación — Breve, con objetivo, estado general, bloqueos y mecanismo de continuación.
- Inventarios estructurados — TASKs, ramas, nodos, jobs, imágenes, modelos y artefactos.
- Índice de evidencia — Rutas durables, identificadores, commits, digests y verificadores.
- Decisiones históricas — Documentos y ADRs que explican por qué se adoptaron ciertas restricciones.
- Procedimiento de recuperación — Secuencia de lectura y operaciones autorizadas.

No copiar todos los logs dentro del resumen.

No resumir eliminando evidencia original.

No confiar exclusivamente en resúmenes generados por el modelo.

Toda afirmación crítica debe relacionarse con una fuente verificable.

La sesión futura debe poder comenzar leyendo el resumen y consultando únicamente la evidencia necesaria para su siguiente acción.

No debe necesitar repetir el análisis de todos los logs para identificar lo que ya está decidido.

## 12. Preservación del paquete de reanudación

El checkpoint debe contener, o referenciar inequívocamente, los siguientes elementos:

1. Identidad del repositorio y commit base.
2. Inventario de ramas y worktrees.
3. Inventario de nodos y VMs.
4. Estado de TASKs.
5. Estado de jobs y procesos.
6. Estado de integración Git.
7. Estado de imágenes Podman.
8. Publicaciones OCI verificadas.
9. Imágenes no publicadas que deban conservarse.
10. Catálogo y ubicaciones de modelos.
11. Datasets y artefactos relevantes.
12. Estado de bases de datos.
13. Dependencias y bloqueos.
14. Decisiones arquitectónicas.
15. Evidencia de verificaciones.
16. Procedimiento de recuperación.
17. Resultado de integridad del checkpoint.

Utilizar las ubicaciones durables existentes.

No generar un ZIP dentro de otro ZIP.

No duplicar artefactos grandes si pueden referenciarse por identidad y ubicación durable.

No introducir numeración artificial en directorios.

Utilizar nombres semánticos de acuerdo con las convenciones actuales del repositorio.

Si se genera un archivo empaquetado, hacerlo solo como copia transportable de información que no tenga otra representación durable adecuada.

Los manifiestos deben permitir comprobar integridad mediante hashes.

No incluir secrets, credenciales, tokens, archivos de autenticación privados ni datos innecesarios.

Distinguir entre evidencia preservada localmente, publicada en Git, publicada en OCI y respaldada mediante otros mecanismos.

Una ruta local no equivale a respaldo externo.

## 13. Cierre distribuido de VMs

La suspensión debe coordinarse a través de las autoridades existentes.

Para cada nodo descubierto:

1. Confirmar identidad y ownership.
2. Confirmar la barrera de nuevas asignaciones.
3. Solicitar drenaje de las ejecuciones admitidas.
4. Preservar cambios y resultados.
5. Confirmar estado de commits y publicación.
6. Preservar imágenes y artefactos necesarios.
7. Confirmar datos persistentes.
8. Verificar ausencia de escritores y consumidores que impidan detener.
9. Solicitar suspensión por el mecanismo autorizado.
10. Registrar el resultado durable.

No apagar la VM controladora antes de preservar y confirmar las respuestas de los nodos accesibles, salvo que la arquitectura tenga un coordinador alternativo autorizado.

No asumir que todos los nodos deben estar encendidos para completar el cierre.

Si una VM está apagada, preservar su última identidad y estado conocido sin despertarla innecesariamente.

Si una VM es inaccesible, mantener su estado como desconocido y conservar el mensaje pendiente de suspensión o reconciliación.

No afirmar que todas las VMs quedaron detenidas si alguna no respondió.

No reasignar a otra VM una TASK cuyo propietario original no ha liberado su ownership de forma verificable.

Evitar ejecuciones duplicadas durante el cierre y durante la recuperación posterior.

## 14. Cancelación final de los trabajos activos

La cancelación final se realizará solamente después de preservar el trabajo y comprobar las condiciones de detención.

Aplicar los mecanismos de cancelación del coordinador, pool, daemon y runtimes correspondientes.

Distinguir entre:

- Cancelación solicitada.
- Cancelación confirmada.
- Proceso terminado.
- Registro asentado.
- Estado recuperable.
- Recursos liberados.

Una señal enviada no demuestra que el trabajo haya terminado.

Un proceso terminado no demuestra que sus resultados estén preservados.

No eliminar worktrees como consecuencia automática de cancelar un job.

No eliminar contenedores, imágenes ni volúmenes como consecuencia automática de detener un runtime.

No cancelar procesos que no pertenezcan a Thyrox.

No utilizar comandos globales que afecten otros proyectos o usuarios.

Si queda una ejecución activa que no puede detenerse de manera segura, registrar su existencia, su propietario y el motivo exacto.

El resultado final podrá ser una suspensión parcial verificada cuando exista un bloqueo real; nunca declarar éxito completo mediante suposiciones.

## 15. Verificación del checkpoint

Antes de declarar concluida la operación, verificar:

- Que no se aceptan nuevas TASKs durante la suspensión.
- Que los jobs terminados tienen resultados asentados.
- Que las TASKs interrumpidas conservan su punto de recuperación.
- Que los cambios Git están preservados o identificados como bloqueados.
- Que los commits publicados tienen referencias verificables.
- Que los worktrees pendientes no fueron eliminados.
- Que los almacenes durables tienen integridad comprobable.
- Que las imágenes OCI críticas están preservadas o explícitamente clasificadas como pendientes de preservación.
- Que los modelos y datasets necesarios son recuperables.
- Que los logs y registros de decisiones siguen accesibles.
- Que no se incluyeron credenciales en el checkpoint.
- Que el procedimiento de reanudación corresponde al estado realmente guardado.

No ejecutar pruebas destructivas sobre el único checkpoint.

Cuando sea posible, realizar una prueba de lectura y reconstrucción del índice de estado desde el paquete preservado.

Verificar también que el procedimiento no dependa de variables, rutas o información que únicamente conoce el coordinador actual.

## 16. Reanudación futura: procedimiento obligatorio

Preparar las instrucciones para el siguiente operador o coordinador.

La reanudación no debe comenzar ejecutando inmediatamente la siguiente TASK.

Primero:

1. Localizar el checkpoint canónico y verificar su integridad.
2. Leer el resumen de reanudación.
3. Comprobar identidad del repositorio y versiones de las autoridades.
4. Reconciliar el estado preservado con Git y los stores actuales.
5. Detectar si hubo actividad después del checkpoint.
6. Verificar los nodos disponibles.
7. Confirmar el estado de ownership y leases.
8. Confirmar que no hay ejecuciones anteriores todavía activas.
9. Verificar modelos y runtimes locales.
10. Reutilizar las imágenes y artefactos OCI ya preservados.
11. Comprobar admisión de recursos.
12. Restablecer los mecanismos de coordinación.
13. Liberar la barrera de suspensión mediante su autoridad.
14. Seleccionar la siguiente TASK mediante `task_continuation` y los mecanismos vigentes.
15. Continuar la autoimplementación con modelos locales.

No repetir automáticamente tareas ya aceptadas.

No reconstruir imágenes por falta de tags si existe una identidad válida recuperable.

No descargar modelos que siguen disponibles.

No fusionar ramas indiscriminadamente.

No asumir que el checkpoint es más reciente que los registros actuales: primero reconciliar.

No volver a solicitar la explicación completa del proyecto cuando las decisiones estén preservadas.

## 17. Ejecución repetible e idempotencia

Este procedimiento debe poder ejecutarse N veces.

Una segunda ejecución debe reconocer el checkpoint anterior y el estado ya preservado.

No duplicar TASKs, imágenes, publicaciones, commits o registros de suspensión.

Cada operación de preservación debe distinguir:

- Ya preservado y verificado.
- Pendiente de preservar.
- En curso.
- Bloqueado.
- Fallido.
- Requiere reconciliación.

Utilizar los identificadores y mecanismos durables existentes para correlacionar intentos.

No inventar nuevos ID de TASK.

No tratar una repetición del comando como una nueva campaña independiente cuando el objetivo de suspensión sigue siendo el mismo.

No sobrescribir evidencia histórica.

Cuando exista evidencia más reciente, registrar su relación con el checkpoint anterior.

Si el procedimiento fue interrumpido durante el propio cierre, la siguiente invocación deberá detectar qué operaciones fueron completadas y continuar desde la primera condición pendiente sin repetir efectos ya confirmados.

## 18. Criterios de aceptación

La suspensión completa será aceptable únicamente cuando:

- A. Descubrimiento — Se identificaron las autoridades, los nodos conocidos, las ramas, los trabajos y las TASKs relevantes, o sus estados desconocidos quedaron expresamente registrados.
- B. Preservación — El trabajo recuperable, las decisiones, los cambios, los datos y la evidencia fueron preservados mediante autoridades durables adecuadas.
- C. Imágenes OCI — Las imágenes que requieren publicación están verificadas remotamente, o permanecen conservadas con un bloqueo explícito que impide su eliminación.
- D. Modelos locales — Los artefactos, configuraciones y cualificaciones necesarios para continuar están disponibles o tienen una ruta de recuperación demostrada.
- E. Integridad — El checkpoint fue verificado sin depender de la memoria del coordinador actual.
- F. Detención — Los trabajos y servicios dentro del alcance fueron detenidos de forma segura o quedaron identificados como pendientes por una causa verificable.
- G. Reanudación — Existe un procedimiento que permite a otro operador recuperar la continuidad sin repetir las auditorías históricas.
- H. Idempotencia — Una segunda ejecución del procedimiento no destruye ni duplica el estado preservado.

No afirmar que el cierre está completo si alguna de estas condiciones falla.

Clasificar el cierre como parcial y documentar los bloqueos.

## 19. Informe final de suspensión

Una vez finalizadas las operaciones permitidas, producir un informe breve respaldado por los registros durables.

Debe incluir:

- Fecha y hora del checkpoint.
- Identidad del repositorio.
- Commit de referencia.
- Estado global del cierre.
- Total de nodos identificados.
- Total de nodos suspendidos.
- Total de nodos no verificados.
- Total de TASKs pendientes, en ejecución, interrumpidas y completadas.
- Total de trabajos cuya terminación fue confirmada.
- Ramas con cambios preservados.
- Cambios pendientes de publicación.
- Imágenes OCI publicadas y verificadas.
- Imágenes que permanecen únicamente locales.
- Publicaciones bloqueadas.
- Modelos y artefactos conservados.
- Bases de datos y estados respaldados.
- Riesgos y bloqueos restantes.
- Ubicación del checkpoint canónico.
- Punto de entrada para la siguiente sesión.
- Procedimiento para reanudar.

No incluir listados enormes en el informe ejecutivo.

Conservar los inventarios completos en los archivos estructurados correspondientes.

No declarar éxito sin evidencia.

## 20. Orden final de ejecución

Ejecuta en este orden:

DISCOVER → QUIESCE → DRAIN → PRESERVE → PUBLISH → VERIFY → STOP → CHECKPOINT → VERIFY RECOVERY

Estas palabras representan las fases funcionales del procedimiento. No implican crear comandos públicos nuevos cuando Thyrox ya tiene operaciones equivalentes.

La preservación puede progresar concurrentemente cuando las dependencias y las autoridades lo permiten.

No comenzar por cancelar procesos ni apagar VMs.

No esperar a que termine todo el proyecto antes de suspenderlo.

No eliminar imágenes, modelos, volúmenes ni evidencia para facilitar artificialmente el cierre.

No usar modelos generativos externos.

No reabrir decisiones arquitectónicas ya resueltas.

No repetir investigaciones completadas.

No inventar nombres de funciones, clases, archivos, comandos o identificadores si ya existen en el proyecto.

Utiliza nombres e identificadores en inglés y comentarios técnicos en español, conforme a las convenciones de Thyrox.

Procede con la suspensión controlada de todo el trabajo bajo las autoridades disponibles, preservando el estado recuperable y dejando un punto de reanudación completo, verificable y reutilizable por cualquier coordinador futuro.
