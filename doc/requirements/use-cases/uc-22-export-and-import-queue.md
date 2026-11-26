# UC-22: Exportar e importar la cola y el historial

- **Objetivo:** el User lleva sus jobs pendientes, su historial o sus listas de URLs a otra instalación, a otro equipo o a otra herramienta, en un formato legible y versionado, sin credenciales y sin que la instalación de destino se apropie de archivos que no escribió.
- **Actor principal:** User
- **Actor secundario:** Programa cliente (consume o produce el formato de intercambio)
- **Disparador:** el User cambia de equipo, reparte la cola entre dos equipos o quiere conservar un registro de lo descargado.
- **Relación:** UC-02 A5 (encolar URLs de un archivo) es el caso mínimo de la importación; UC-23 resuelve otra necesidad: restaurar la misma instalación.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí: formato de intercambio versionado e identidad de los jobs importados
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente. Condiciones técnicas: D-16 y D-21.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - **Seal:** exportar e importar el historial y las listas de URLs.
  - **Revisión de exclusiones:** la exclusión «la cola no es un historial» no se sostiene: los jobs terminados ya forman un historial que `list` muestra ([análisis, §12](../requirements-analysis.md#12-reconciliación-de-exclusiones)).

## Breve descripción

`export` escribe un documento JSON versionado con los jobs seleccionados: URL, download options, estado, motivo de fallo, título, media key, relación con su playlist y ruta del archivo final como dato informativo. `export --urls` escribe solo las URLs, una por línea. `import` crea jobs nuevos `PENDING` a partir de un documento y nunca transfiere estados, propiedad, reclamaciones ni parciales ([BR-36](../business-rules.md)).

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `export ARCHIVO [--status ...]`.
2. El sistema lee los jobs en una transacción de solo lectura.
3. El sistema escribe el documento con la versión del formato, la versión del programa y la fecha, sin credenciales ni rutas de reclamaciones ([BR-34](../business-rules.md)).
4. En la otra instalación, el User ejecuta `import ARCHIVO`.
5. El sistema valida el documento completo: versión, campos y URLs.
6. El sistema crea un job `PENDING` por cada entrada que requiere trabajo, con sus download options, en una sola transacción. Las playlists se reconstruyen con su relación con las entradas.
7. El sistema muestra cuántos jobs creó, cuántos omitió por duplicados y por qué.

## Flujos alternativos

- **A1. Solo URLs:** `[estado: ausente]` `export --urls` y `enqueue --from-file` (UC-02 A5).
- **A2. Historial terminado:** `[estado: ausente]` `import --as-history` registra los jobs terminados como referencia de solo lectura, sin propiedad sobre sus archivos ([BR-36](../business-rules.md)).
- **A3. Duplicados:** `[estado: ausente]` una entrada con la misma identidad que un job activo (BR-32) se omite y se informa.
- **A4. Rutas distintas en el destino:** `[estado: ausente]` las carpetas de descarga se toman de la configuración de destino, salvo `--keep-paths`; una ruta inexistente se informa sin crear nada.
- **A5. Documento de una versión anterior del formato:** `[estado: ausente]` se convierte si la versión está soportada; si no, E2.
- **A6. `run` en ejecución:** `[estado: ausente]` la importación funciona igual que `enqueue` (SQLite en modo WAL).

## Excepciones

- **E1. Documento inválido o incompleto:** `[estado: ausente]` no se crea ningún job; el sistema nombra la entrada y el campo; código `2`.
- **E2. Versión del formato no soportada:** `[estado: ausente]` código `2`.
- **E3. Base de datos ocupada:** `[estado: ausente]` como UC-02 A3; nada se importa.

## Garantías

- **De éxito:** los jobs importados están en la cola con sus opciones.
- **Mínima:**
  - una importación fallida no deja jobs a medias;
  - nunca se crea una reclamación ni se toma la propiedad de un archivo existente;
  - nunca se exporta un secreto.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-17, BR-32, BR-34 y BR-36.
- **Requisitos suplementarios:** SUP-I02 y SUP-SEC01.
- **Restricciones:** copiar `queue.sqlite3` no es una exportación: arrastra los ids, las reclamaciones y la propiedad (UC-06 A8).
- **Dependencias:** UC-02 y UC-04.

## Criterios de aceptación

1. Exportar e importar en una cola vacía reproduce los jobs pendientes con las mismas opciones y relaciones.
2. Un documento con una sola entrada inválida no crea ningún job.
3. Importar nunca hace que un job se considere dueño de un archivo existente.
4. Con valores trampa, ningún secreto aparece en el documento.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Ida y vuelta, versiones del formato, documentos inválidos | Cualquier sistema |
| Importación con archivos ya presentes en el destino | Cualquier sistema |
