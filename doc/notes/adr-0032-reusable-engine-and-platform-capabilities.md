# ADR-0032: Motor reutilizable con contratos independientes de la interfaz y capacidades de plataforma por responsabilidad

- **Estado:** Aceptada. La orientación es una disposición del Responsable (instrucción 2.3.0); el diseño concreto de cada contrato es propuesto en la [Parte 3 del diseño](../design/03-target-architecture-and-evolution.md).
- **Fecha:** 2026-11-26
- **Relación:**
  - **aclara** [ADR-0001](adr-0001-project-scope.md): la CLI es la primera interfaz, no la única;
  - **aclara** [ADR-0004](adr-0004-windows-x64-target-platform.md): Windows x64 es la primera plataforma, no una restricción permanente;
  - **amplía** [ADR-0017](adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md) A: el ensamblaje del producto es uno solo y cada interfaz ensambla su presentación;
  - **acota** [ADR-0008](adr-0008-process-based-worker-pool.md): el proceso es el mecanismo de escritorio, no el contrato.

## Contexto

El Responsable dispuso que habrá aplicaciones para Windows (gráfica), Android e iOS, sin duplicar reglas ni reescribir el motor. Solo están autorizados la CLI y Windows x64.

La inspección del código (Parte 3, §2) muestra:
- las reglas y los casos de uso ya no dependen de la CLI;
- pero el ensamblaje del producto y la secuencia de ejecución viven en `command_line` (A-1);
- la observación expone el transporte de `workers` (A-2);
- las consultas devuelven la entidad interna (A-3);
- las identidades de los outputs son rutas de Windows (A-6).

La documentación oficial y los proyectos de referencia muestran que en Android e iOS Python solo se ejecuta embebido. Además, iOS no admite procesos, y Android no los soporta oficialmente, aunque las referencias los usan.

## Opciones consideradas

1. **Tres productos con sus propias reglas.** Rechazada por el Responsable: duplica las reglas.
2. **Reestructurar ahora en capas genéricas** (`domain/`, `application/`, `infrastructure/`) **con un `PlatformAdapter`.** Rechazada:
   - contradice ADR-0016 y el principio de nombres #9;
   - un adaptador único obliga a cada plataforma a implementar responsabilidades que no tiene (ISP).
3. **Convertir el producto en cliente-servidor.** Rechazada por ahora: añade una frontera de red sin necesidad demostrada (Parte 3, §7.4).
4. **Conservar los componentes y separar solo lo que impide reutilizar.** Contratos públicos por responsabilidad y una capacidad por dimensión variable, elegida en un único ensamblaje. **Elegida.**

## Decisión

1. **Un modelo funcional.** Los 26 casos de uso son únicos para todas las interfaces. Las diferencias de plataforma se expresan como escenarios, restricciones, requisitos suplementarios, capacidades y criterios de aceptación.
2. **Contratos públicos independientes de la presentación:**
   - operaciones (los casos de uso de `job_queue`);
   - vistas versionadas, distintas de las entidades internas;
   - eventos con el estado del job, sin el transporte del pool;
   - errores con código;
   - progreso con significado;
   - capacidades.
   Ningún consumidor interpreta texto de la CLI, de yt-dlp ni de FFmpeg.
3. **Un ensamblaje del producto.** Abrir la instalación, componer las implementaciones del ambiente y ejecutar la sesión (recuperar antes de ejecutar) es responsabilidad de un componente propio (nombre candidato `queue_installation`). Cada interfaz ensambla solo su presentación. Se introduce cuando exista el segundo consumidor real (contrato JSON o API Python de D-17).
4. **Capacidades por responsabilidad.** Ejecución, terminación, almacenamiento, ubicación de la instalación, secretos, programación, avisos y multimedia tienen cada una su contrato pequeño, con un consumidor real. Se seleccionan en el ensamblaje, con el patrón de [ADR-0013](adr-0013-process-tree-terminator-abstraction.md) y [ADR-0029](adr-0029-process-tree-termination-on-windows.md). No hay un adaptador de plataforma único.
5. **El proceso es un mecanismo, no un contrato.** En escritorio, un job se ejecuta en un proceso para poder terminar yt-dlp y sus hijos. El contrato funcional es una unidad de ejecución aislable y administrable.
6. **Las identidades no dependen de rutas** ([ADR-0033](adr-0033-output-identity-and-storage-references.md), propuesta).
7. **Ejecución local** para Windows CLI y Windows GUI. Para móvil no se elige alternativa: los contratos no deben impedir ni la ejecución local ni la híbrida. No se construye un servidor.
8. **No se elige tecnología** gráfica, móvil ni de transporte en esta etapa.

## Consecuencias

- **Activación de reglas:**
  - se activan ya dos contratos de imports que hoy se cumplen: los componentes no importan `argparse`, y `jobs` no importa mecanismos variables;
  - se activarán al separar el ensamblaje y la observación: la CLI no importa `sqlite3` ni las implementaciones, y la presentación no consume `WorkerMessage`.
- La planificación de E3 incluye la separación del ensamblaje en su primera unidad con un segundo consumidor.
- **Lo que no cambia:**
  - la estructura de paquetes y los nombres;
  - los contratos vigentes;
  - `multiprocessing` y los Job Objects;
  - las dependencias fijadas;
  - la distribución LGPL.
- La viabilidad en iOS de UC-03, UC-04, UC-15, UC-21, UC-24 y UC-26 queda *no demostrada*. Depende de cualificar un proveedor de retos de JavaScript en proceso y una unión sin ejecutable externo.
