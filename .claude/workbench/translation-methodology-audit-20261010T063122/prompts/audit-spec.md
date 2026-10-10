# Encargo literal del ejecutor (2026-10-10T06:2xZ), transcrito sin cambios de contenido

Precisión posterior del ejecutor, en el mismo intercambio: *«sin embargo, lo anterior no solo
menciona ha si en este momento thyrox tiene implementado el mecanismo, aplica a TODO lo que se
ha hecho aqui, usando como ejemplo el PROVIDER de thyrox, si lo puedes replicar genera una
nueva VM»*. Y el marco: *«se ejecutara con un modelo local con el razonamiento encendido»*.

---

# Auditoría, integración y documentación de la metodología y del procedimiento de traducción de ai-course-notes

## 1. Objetivo principal

Realiza un análisis exhaustivo de la metodología y del procedimiento operativo que actualmente utilizas para traducir el repositorio `ai-course-notes`, empleando exclusivamente modelos locales a través de las capacidades existentes de Thyrox.

El propósito es:

1. Verificar cómo se está ejecutando realmente la traducción.
2. Identificar los componentes de Thyrox que ya están implementados y pueden reutilizarse.
3. Integrar los cambios pertinentes de `feature/fresh-clone-bootstrap` sin perder el trabajo de nuestra rama.
4. Analizar `Qwen3.5-9B.txt` y contrastar sus recomendaciones con las capacidades reales de los binarios, el modelo y el entorno.
5. Identificar configuraciones apropiadas para las distintas actividades de traducción.
6. Evaluar la calidad, reproducibilidad, eficiencia y trazabilidad del proceso.
7. Diferenciar claramente metodología, procedimiento e implementación.
8. Documentar los resultados dentro de `ai-course-notes/docs`.
9. Corregir las deficiencias demostradas mediante evidencia, reutilizando preferentemente los mecanismos existentes.

**No debes sustituir los mecanismos de Thyrox por implementaciones independientes sin demostrar primero que las capacidades existentes son insuficientes.**

## 2. Verificación inicial del entorno

Antes de modificar archivos o ejecutar nuevas tareas, identifica y registra:

- Rama actual, `HEAD`, estado del working tree y cambios no publicados.
- Trabajos activos, pendientes, fallidos y completados.
- Modelos locales disponibles y sus identificadores verificables.
- Runtime utilizado realmente para inferencia.
- Configuración efectiva del modelo que participa en la traducción.
- Componentes y paquetes de Thyrox actualmente utilizados.
- Recursos disponibles: CPU, memoria, disco, contexto y capacidad de concurrencia.
- Artefactos y resultados producidos por ejecuciones anteriores.

Distingue expresamente entre:

- Capacidad declarada.
- Capacidad implementada.
- Capacidad probada.
- Capacidad integrada.
- Capacidad utilizada realmente durante una ejecución.

La existencia de un componente, paquete, función o prueba no demuestra por sí misma que esté siendo utilizado.

Para cada afirmación relevante, proporciona evidencia identificable.

## 3. Uso obligatorio de modelos locales

Comprueba que las operaciones de traducción, revisión, validación semántica y demás actividades de inferencia estén utilizando modelos locales mediante Thyrox.

No utilices proveedores externos, API comerciales ni mecanismos de fallback hacia modelos externos.

Verifica la cadena completa:

`ai-course-notes → Thyrox → selección del modelo → managed runtime → inferencia local → resultado → validación`

Identifica cualquier punto en el que la ejecución se desvíe de esta arquitectura.

El modelo del coordinador no debe utilizarse como sustituto del modelo local para realizar las traducciones ni para resolver silenciosamente fallas del pipeline.

Distingue el trabajo de coordinación del trabajo de inferencia, y aporta evidencia de cuál modelo produjo cada resultado.

## 4. Integración de feature/fresh-clone-bootstrap

Analiza la relación entre nuestra rama actual y `feature/fresh-clone-bootstrap`.

Antes de integrar:

1. Identifica los commits exclusivos de cada rama.
2. Determina las modificaciones realizadas a los paquetes y mecanismos de Thyrox.
3. Localiza los componentes que podrían beneficiar al proceso de traducción.
4. Revisa los cambios locales no confirmados.
5. Identifica riesgos de conflictos, regresiones y pérdida de trabajo.
6. Preserva los trabajos activos y sus artefactos.
7. Identifica posibles colisiones de identificadores de tareas, considerando que pueden existir identificadores iguales en diferentes ramas.

Integra los cambios mediante el mecanismo Git apropiado, preservando la trazabilidad y sin sobrescribir modificaciones existentes.

No realices un merge indiscriminado ni reproduzcas manualmente código que ya exista en la otra rama.

Después de la integración, ejecuta las pruebas pertinentes y comprueba que los mecanismos requeridos por `ai-course-notes` continúan funcionando.

Si existe un bloqueo real, conserva la evidencia y continúa con las actividades independientes que puedan realizarse de forma segura.

## 5. Descubrimiento y reutilización de capacidades existentes

Antes de implementar o modificar mecanismos, investiga lo que Thyrox ya proporciona.

No limites el análisis al nombre de los archivos. Inspecciona el código fuente, las firmas, los consumidores, las pruebas, la documentación, los binarios y las reglas arquitectónicas.

Considera, cuando corresponda:

- Catálogo y selección de modelos.
- Managed runtimes.
- Ejecución de inferencia local.
- Configuración de contextos y parámetros de generación.
- Orquestación y distribución de trabajos.
- Concurrencia y control de recursos.
- GNU Parallel y otros mecanismos existentes de ejecución.
- Administración de trabajos en segundo plano.
- Supervisión y recuperación de procesos.
- Registros de ejecución y auditoría.
- Persistencia, cache y recuperación de resultados.
- Semantic search y embeddings locales.
- Pruebas y mecanismos de aceptación.
- Contenedores y ejecución mediante `podman-execution-primitive`.
- Mecanismos documentados en `_references`, cuando sean pertinentes.

No supongas que todos estos mecanismos están disponibles o integrados. Verifícalo.

Para cada capacidad relevante, determina:

| Clasificación | Significado |
|---|---|
| REUSE | Existe, funciona y puede utilizarse directamente. |
| EXTEND | Existe, pero requiere una extensión demostrablemente necesaria. |
| INTEGRATE | Existe, pero todavía no está conectado al flujo de traducción. |
| REPAIR | Existe, pero presenta un defecto reproducible. |
| MISSING | No se encontró una capacidad equivalente después de una búsqueda suficiente. |
| NOT_APPLICABLE | Existe, pero no resulta pertinente para esta operación. |

No crees nombres nuevos de archivos, clases, funciones o identificadores cuando ya existan nombres adecuados en el proyecto.

Conserva los identificadores en inglés y los comentarios en español técnico, respetando las convenciones existentes y los principios de clean code.

## 6. Análisis de Qwen3.5-9B.txt

Lee íntegramente `Qwen3.5-9B.txt`.

Identifica las recomendaciones técnicas que sean aplicables a la traducción y compáralas con:

- El modelo local realmente disponible.
- Su cuantización y formato.
- El runtime empleado.
- La versión y capacidades del binario.
- El tamaño efectivo de contexto.
- Las plantillas de conversación.
- Los parámetros de muestreo y generación.
- El presupuesto de tokens.
- Los mecanismos de procesamiento por lotes.
- Los límites de memoria y concurrencia.

Analiza especialmente los parámetros documentados, incluidos, cuando correspondan:

`--temp`, `--top-p`, `--top-k` y `--min-p`.

No copies configuraciones sin verificar su compatibilidad.

No presupongas que una configuración recomendada para generación general sea óptima para traducción.

Cuando sea necesario, realiza evaluaciones controladas y reproducibles con muestras representativas de traducción.

Documenta:

- Configuración original.
- Configuración propuesta.
- Fundamento técnico.
- Evidencia de compatibilidad.
- Resultados comparativos.
- Impacto en calidad, velocidad, memoria y consumo de tokens.
- Decisión final.

No introduzcas categorías heredadas de clasificación de tareas que hayan quedado obsoletas. Utiliza la terminología vigente en las autoridades aplicables y diferencia el nivel de esfuerzo de los parámetros de muestreo.

## 7. Auditoría exhaustiva de la metodología de traducción

Reconstruye la metodología realmente aplicada, no una metodología idealizada.

Investiga, como mínimo:

### 7.1 Análisis del contenido

¿Cómo se identifican los archivos que requieren traducción?

¿Cómo se detectan formatos, idiomas, elementos estructurales y dependencias?

¿Cómo se clasifican los contenidos técnicos y cuáles deben permanecer sin traducir?

### 7.2 Preparación

¿Cómo se divide el contenido?

¿Cómo se establecen los límites de contexto y tamaño de los segmentos?

¿Cómo se preservan código, comandos, nombres de archivos, referencias, enlaces, identificadores, fórmulas y bloques Markdown?

¿Cómo se gestiona la terminología?

### 7.3 Inferencia

¿Cómo selecciona Thyrox el modelo?

¿Cómo se construyen los prompts?

¿Cómo se configuran los parámetros?

¿Cómo se administran tokens, contexto y memoria?

¿Cómo se distribuyen las tareas y se controla la concurrencia?

### 7.4 Validación

¿Cómo se verifica la fidelidad semántica?

¿Cómo se detectan omisiones, adiciones no justificadas y alteraciones de significado?

¿Cómo se comprueba la preservación estructural?

¿Cómo se validan código, matemáticas, enlaces y referencias?

¿Qué pruebas automatizadas existen y cuáles faltan?

### 7.5 Revisión y corrección

¿Cómo se identifican los errores?

¿Cómo se decide si un segmento debe reintentarse?

¿Cómo se evita repetir traducciones aceptadas?

¿Cómo se determina que un resultado es aceptable?

### 7.6 Persistencia y trazabilidad

¿Cómo se registran los segmentos traducidos?

¿Cómo se vincula cada salida con su entrada, modelo, configuración y ejecución?

¿Cómo se conserva el progreso después de una interrupción?

¿Cómo se evita perder trabajo o reprocesar contenido?

### 7.7 Evaluación del rendimiento

Identifica los mecanismos utilizados para medir:

- Tokens procesados.
- Tiempo de inferencia.
- Rendimiento por modelo.
- Uso de memoria.
- Concurrencia efectiva.
- Retrabajo.
- Tasa de errores.
- Cobertura de traducción.
- Calidad de los resultados.

No inventes métricas ni resultados. Si no existen mediciones, registra la ausencia.

## 8. Diferencia entre metodología y procedimiento

Documenta ambos conceptos por separado cuando el análisis demuestre que tienen propósitos diferentes.

### Metodología

Debe explicar por qué se eligen determinadas estrategias, modelos, mecanismos de validación, criterios de segmentación y métodos de evaluación.

Incluye decisiones, alternativas, justificaciones, criterios de aceptación, limitaciones y evidencia.

### Procedimiento

Debe explicar cómo reproducir una ejecución completa utilizando el código y los mecanismos reales.

Incluye:

1. Prerrequisitos.
2. Verificaciones iniciales.
3. Preparación del entorno.
4. Selección y configuración del modelo.
5. Preparación del contenido.
6. Ejecución de la traducción.
7. Supervisión y control de recursos.
8. Validaciones y pruebas.
9. Manejo de errores.
10. Reanudación después de interrupciones.
11. Criterios de aceptación.
12. Publicación o integración de los resultados.
13. Conservación de evidencias.

Los comandos documentados deben corresponder a mecanismos existentes y haber sido verificados.

No presentes pseudocódigo como si fuera una operación validada.

## 9. Documentación en ai-course-notes/docs

Inspecciona primero la estructura documental actual.

Identifica los documentos existentes que ya describen partes de la metodología o del procedimiento.

Actualízalos o extiéndelos antes de proponer documentos nuevos.

Mantén referencias entre:

- Metodología.
- Procedimiento.
- Arquitectura utilizada.
- Configuración de modelos.
- Pruebas.
- Evidencias.
- Limitaciones conocidas.

Distingue explícitamente:

- Comportamiento actual verificado.
- Comportamiento propuesto.
- Funcionalidad pendiente.
- Decisiones todavía no validadas.

La documentación debe permitir que otra sesión reproduzca el procedimiento sin depender del contexto de esta conversación.

## 10. Ejecución de pruebas y validación

Utiliza las pruebas y mecanismos de aceptación existentes en Thyrox y `ai-course-notes`.

Verifica que las pruebas correspondan realmente a los componentes utilizados durante la traducción.

Cuando falten pruebas, determina primero si pueden ampliarse las existentes.

Para cada cambio aplicado:

1. Registra el comportamiento previo.
2. Identifica la causa de la deficiencia.
3. Aplica el cambio mínimo justificable.
4. Ejecuta las pruebas correspondientes.
5. Verifica que no existan regresiones.
6. Registra el resultado y su evidencia.

No declares un componente funcional únicamente porque compila, porque tiene pruebas aisladas o porque una ejecución terminó con código cero.

## 11. Conservación y seguridad operativa

Preserva los trabajos, resultados y cambios existentes.

No elimines modelos, imágenes, volúmenes, caches, registros ni artefactos sin conocer sus consumidores, su estado y la política aplicable.

Para operaciones de contenedores administrados, respeta la autoridad arquitectónica de Thyrox y su mecanismo obligatorio de ejecución.

No utilices almacenamiento efímero para evidencias que deban conservarse.

No alteres innecesariamente configuraciones globales ni interrumpas trabajos activos.

Si existe una desviación, registra el comportamiento observado, la autoridad correspondiente, el impacto y la resolución.

## 12. Resultados obligatorios

Al concluir, entrega:

**A. Estado real de la ejecución**

Qué está funcionando, qué se utiliza realmente, qué permanece pendiente y qué presenta defectos.

**B. Integración de ramas**

Commits integrados, conflictos encontrados, resolución y pruebas.

**C. Matriz de capacidades reutilizadas**

Componentes encontrados, clasificación REUSE/EXTEND/INTEGRATE/REPAIR/MISSING/NOT_APPLICABLE y evidencia.

**D. Análisis del modelo local**

Configuraciones originales y finales, compatibilidad y resultados de validación.

**E. Auditoría metodológica**

Descripción completa del método de traducción, sus decisiones y sus criterios de calidad.

**F. Procedimiento reproducible**

Pasos, comandos verificados, entradas, salidas, recuperación y aceptación.

**G. Documentación**

Rutas concretas de los archivos actualizados dentro de `ai-course-notes/docs`.

**H. Pruebas y evidencias**

Casos ejecutados, resultados, defectos y regresiones.

**I. Pendientes**

Únicamente las deficiencias que no hayan podido resolverse, junto con su causa y dependencias.

## 13. Reglas de ejecución

No te detengas únicamente para producir reportes parciales si existen actividades independientes que pueden continuar ejecutándose de manera segura.

No reemplaces mecanismos existentes por scripts ad hoc.

No introduzcas dependencias de modelos externos.

No confundas documentación de una capacidad con evidencia de su funcionamiento.

No declares pruebas satisfactorias sin resultados verificables.

No realices refactorizaciones ajenas al objetivo.

Conserva la trazabilidad de todos los cambios.

**El resultado esperado no es solamente documentación: es una metodología identificada, un procedimiento reproducible, una integración verificada con Thyrox y evidencia de que la traducción utiliza efectivamente modelos locales.**
