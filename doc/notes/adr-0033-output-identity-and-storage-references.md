# ADR-0033: Identidad de los outputs separada de su ubicación (referencias de almacenamiento)

- **Estado:** Propuesta (Analysis and Design, instrucción 2.3.0). Se acepta al diseñar el esquema de D-15 en E3.
- **Fecha:** 2026-11-26
- **Relación:**
  - **generaliza** [ADR-0030](adr-0030-final-file-ownership-claims.md), sin cambiar sus garantías;
  - realiza D-15 y D-16 del [análisis](../requirements/requirements-analysis.md#9-decisiones);
  - diseño en la [Parte 3, §6](../design/03-target-architecture-and-evolution.md#6-contratos-fundamentales-reconciliados).

## Contexto

Hoy un job tiene un solo output, `Job.output_path`. Es una ruta, y su unicidad la garantizan:
- el índice `unique_output_path`;
- la reclamación de ADR-0030, una ruta canonizada con `realpath` y `normcase` y un archivo `.claim` creado con `O_EXCL`.

D-15 aprobó cero, uno o N outputs por job. La normalización de rutas de Windows no es una identidad universal:
- un traslado, una restauración en otra máquina o una importación cambian la ruta sin cambiar el output;
- en Android un recurso elegido por el User es un URI de documento con permiso persistente;
- en iOS es una URL del selector de documentos, con un bookmark para conservar el acceso (documentación oficial).

## Decisión propuesta

1. **Identidad del output:** `(identidad del job, clave del output)`. La clave es el tipo y su discriminante (`video`, `audio`, `subtitle:es`, `thumbnail`, `description`).
2. **Referencia de almacenamiento:** describe cómo se llega al archivo en el ambiente que lo produjo. En Windows es la ruta. No forma parte de la identidad y puede reasignarse.
3. **Propiedad:** la reclamación del owner token se hace sobre la referencia de almacenamiento.
   - En Windows y POSIX sigue siendo el mecanismo de ADR-0030, extendido a cada output, sidecars incluidos (R-30).
   - El mecanismo móvil está por cualificar; no hay garantía de `O_EXCL` en SAF.
4. **Destino:** el destino solicitado por el User se guarda como preferencia de la petición. La ubicación asignada es la referencia de cada output.
5. **Transición:**
   - `output_path` se conserva como la referencia de almacenamiento del output principal en Windows mientras tenga consumidores;
   - la migración crea el output principal de cada job completado, sin reescribir reclamaciones;
   - no se modifica ninguna migración publicada.
6. **Nombre en el código:** `output` (por ejemplo `JobOutput`), nunca `result`. «Result» ya designa el resultado de una operación (`CancelJobResult`, `RunQueueResult`); se respeta «una palabra por concepto».

## Consecuencias

- Exportar, importar y restaurar conservan la identidad de los outputs y reasignan su ubicación (UC-22, UC-23).
- La verificación (UC-26, BR-38) y el borrado autorizado (UC-25, BR-17) operan por output.
- La detección de colisiones actual se conserva como el mecanismo de Windows para comparar ubicaciones.
- No se introduce una abstracción de almacenamiento antes de implementar D-15: la implementación de Windows sigue usando rutas.
- **Pendiente:** el contrato de reclamación en Android e iOS.
