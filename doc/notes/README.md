# Registro de decisiones de arquitectura (ADR)

Cada decisión se registra en un archivo con: contexto, opciones consideradas, decisión y consecuencias.

| ADR | Decisión | Estado |
|---|---|---|
| [0001](adr-0001-project-scope.md) | Alcance inicial: cola de descargas sin GUI | Aceptada (nombre actualizado por 0015; aclarada por 0032: la CLI es la primera interfaz) |
| [0002](adr-0002-pinned-yt-dlp-version.md) | Versión de yt-dlp fijada (2026.10.26) | Aceptada |
| [0003](adr-0003-packaging-with-uv-and-pyproject.md) | Empaquetado con uv y `pyproject.toml` | Aceptada |
| [0004](adr-0004-windows-x64-target-platform.md) | Plataforma objetivo: Windows x64 | Aceptada (aclarada por 0032: primera plataforma, no restricción permanente) |
| [0005](adr-0005-vendored-ffmpeg-lgpl-shared.md) | ffmpeg incluido en el repositorio (LGPL compartida) | Aceptada (build concreta en 0018) |
| [0006](adr-0006-ffmpeg-resolution-and-verification.md) | Resolución y verificación de ffmpeg | Aceptada (término actualizado por 0014) |
| [0007](adr-0007-project-license-unlicense.md) | Licencia del proyecto: The Unlicense | Aceptada (material de referencia en 0025) |
| [0008](adr-0008-process-based-worker-pool.md) | Pool fijo de workers en procesos | Aceptada (a validar en el prototipo; completada por 0013; acotada por 0032; revisada por 0034: Preserve y Specialize como mecanismo de escritorio) |
| [0009](adr-0009-playlist-expansion-into-jobs.md) | Expansión de playlists en trabajos individuales | Aceptada (ajustada por 0012) |
| [0010](adr-0010-sqlite-persistent-queue.md) | Cola persistente en SQLite | Aceptada (términos actualizados por 0014) |
| [0011](adr-0011-code-conventions.md) | Convenciones de código | Aceptada (pendientes resueltos en 0017 y 0019) |
| [0012](adr-0012-no-download-archive-no-database-triggers.md) | Sin `download_archive` ni triggers con reglas de negocio | Aceptada |
| [0013](adr-0013-process-tree-terminator-abstraction.md) | Abstracción `ProcessTreeTerminator` | Aceptada |
| [0014](adr-0014-use-case-structure-and-vocabulary.md) | Estructura por casos de uso y vocabulario | Aceptada (estructura reemplazada por 0016; prefijo actualizado por 0015) |
| [0015](adr-0015-project-and-package-name.md) | Nombre del proyecto y del paquete: `queued_media_downloader` | Aceptada (carpeta ajustada por 0016) |
| [0016](adr-0016-component-packages-and-flat-layout.md) | Paquetes por componente y paquete en la raíz del proyecto | Aceptada (completada por 0017) |
| [0017](adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md) | API pública por componente, ensamblaje en el programa y grafo comprobado | Aceptada (A ampliada por 0032: un ensamblaje del producto) |
| [0018](adr-0018-ffmpeg-build-selection.md) | Build de ffmpeg: BtbN, rama 9.0, LGPL compartida win64 | Aceptada |
| [0019](adr-0019-code-quality-tools.md) | Herramientas de calidad (Ruff, mypy) y comentarios en español | Aceptada |
| [0020](adr-0020-repository-branching-and-lfs.md) | Repositorio en GitHub, ramas *trunk-based* y Git LFS | Aceptada |
| [0021](adr-0021-tdd-and-windows-validation-without-ci.md) | TDD y validación en Windows sin integración continua | Aceptada |
| [0022](adr-0022-hybrid-approach-and-task-decomposition.md) | Enfoque híbrido (predictivo y ágil) y descomposición en slices | Aceptada (tamaño de tarea ajustado por 0023) |
| [0023](adr-0023-roles-and-scope-boxed-iterations.md) | Roles e iteraciones delimitadas por alcance | Aceptada (corregida por 0024 y 0025) |
| [0024](adr-0024-verification-by-tdd-and-review-focus.md) | Verificación por TDD y revisión centrada en las pruebas | Aceptada |
| [0025](adr-0025-reference-material-distribution.md) | Distribución del material de referencia | Aceptada |
| [0026](adr-0026-smart-app-control-precondition.md) | Smart App Control desactivado como precondición de E1 | Aceptada |
| [0027](adr-0027-video-links-inside-lists.md) | Un enlace a un video dentro de una lista descarga solo el video | Aceptada |
| [0028](adr-0028-playlist-child-output-template.md) | Plantilla de salida de los hijos de una playlist | Aceptada |
| [0029](adr-0029-process-tree-termination-on-windows.md) | Implementación de `ProcessTreeTerminator` (D1) | Aceptada; validación en Windows pendiente |
| [0030](adr-0030-final-file-ownership-claims.md) | Propiedad de los archivos finales mediante reclamaciones | Aceptada; validación en Windows pendiente (generalización propuesta en 0033) |
| [0031](adr-0031-site-waits-and-network-waits.md) | Aplazar jobs y esperar al sitio, a la red y al disco, sin PO Tokens ni cuentas | Propuesta |
| [0032](adr-0032-reusable-engine-and-platform-capabilities.md) | Motor reutilizable con contratos independientes de la interfaz y capacidades de plataforma por responsabilidad | Aceptada (diseño concreto propuesto) |
| [0033](adr-0033-output-identity-and-storage-references.md) | Identidad de los outputs separada de su ubicación | Propuesta cualificada (contrato definido para E3) |
| [0034](adr-0034-single-coordinator-and-isolated-execution.md) | Coordinación única con ejecución intercambiable; el pool de procesos como mecanismo de escritorio | Propuesta, recomendada con evidencia |

## Convenciones de este registro

- Nombre de archivo: `adr-NNNN-<titulo-en-ingles>.md` ([ADR-0011](adr-0011-code-conventions.md)).
- Una decisión aceptada no se edita para cambiarla: se crea un ADR nuevo que la reemplaza y se marca la anterior como *Reemplazada por ADR-NNNN*. Si el ADR nuevo solo ajusta una parte o renombra términos, la anterior recibe una nota que remite a él.
