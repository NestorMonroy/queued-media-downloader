# UC-25: Administrar los resultados descargados

- **Objetivo:** el User sabe qué archivos produjo cada job, dónde están, cuáles faltan y cuánto ocupan. Puede eliminar sus propios resultados con autorización explícita, sin que el sistema toque nunca un archivo que no escribió.
- **Actor principal:** User
- **Actor secundario:** Sistema de archivos
- **Disparador:** el User busca lo descargado, quiere liberar espacio o nota que falta un archivo.
- **Relación:** UC-09 muestra un job y ahora también sus resultados (A6). UC-10 purga registros y nunca archivos; su A5 (purgar con archivos) pasa a este caso de uso. UC-26 verifica la integridad.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí: requiere el registro de los resultados de cada job (D-15)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: parcial (`output_path`, un archivo por job). Condiciones técnicas: D-11 y D-15.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:**
  - **YTDownload-2026:** rutas de los archivos de cada descarga y borrado con vista previa; también un antiejemplo: borra la carpeta entera.
  - **Seal y VoiceStudio:** borrar el registro con su archivo.
  - **Decisión D-11.**

## Breve descripción

`files ID` lista los resultados registrados del job: tipo, ruta, tamaño, y si existe o falta. `files --missing` lista los resultados que faltan en toda la cola. `files --usage` muestra el espacio por estado, playlist o carpeta. `files delete ID...` borra los resultados propios del job, con vista previa y confirmación.

Un resultado es propio si:
- el job lo registró;
- conserva su reclamación con su owner token;
- y el archivo sigue en su ruta ([BR-31](../business-rules.md)).

Un archivo no es del producto solo por estar en la carpeta de descargas.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `files ID`.
2. El sistema lee los resultados registrados del job.
3. El sistema comprueba cada ruta en el disco y muestra el tipo, la ruta, el tamaño y su estado (presente, ausente o cambiado de tamaño).

## Flujos alternativos

- **A1. Eliminar resultados propios:** `[estado: ausente]` `files delete ID...` muestra primero una vista previa (archivos, tamaño total y archivos que no se tocarán) sin borrar nada, y borra solo con `--confirm`. Solo borra resultados propios ([BR-31](../business-rules.md)); nunca carpetas enteras ni archivos sin reclamación. Al terminar, suelta las reclamaciones de lo borrado y el job conserva su registro con los resultados marcados como eliminados.
- **A2. Purgar y borrar:** `[estado: ausente]` `purge --delete-files` aplica A1 a los jobs purgados (UC-10 A5).
- **A3. Resultados que faltan:** `[estado: ausente]` `files --missing`. El sistema no cambia el estado del job: un job `COMPLETED` cuyo archivo falta sigue `COMPLETED` (UC-06 A9) y se informa.
- **A4. Archivos huérfanos:** `[estado: ausente]` `files --orphans` lista los archivos de la carpeta de descargas que tienen reclamación pero ningún job, y las reclamaciones sin archivo. Solo informa. Soltar las reclamaciones de jobs inexistentes ya lo hace `purge` (UC-10).
- **A5. Espacio usado:** `[estado: ausente]` `files --usage`.
- **A6. Mover resultados:** `[estado: ausente]` **pendiente de cualificación**. Moverlos rompe la relación ruta–reclamación; solo se admitiría moviendo juntos el archivo y su reclamación y actualizando el registro (D-11).

## Excepciones

- **E1. El archivo cambió desde que el job lo escribió** `[estado: ausente]` (tamaño distinto, o la verificación de UC-26 falla): A1 no lo borra sin `--force`; la vista previa lo indica.
- **E2. El borrado falla** `[estado: ausente]` (archivo abierto, permisos): se informa por archivo y se sigue con los demás; las reclamaciones de lo no borrado se conservan.
- **E3. Job inexistente:** `[estado: ausente]` código `2`.

## Garantías

- **De éxito:** el User ve todos los resultados de sus jobs y su estado.
- **Mínima:**
  - nunca se borra un archivo sin confirmación;
  - nunca se borra un archivo ajeno, sin reclamación propia, ni una carpeta entera.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-17, BR-18, BR-29 y BR-31.
- **Requisitos suplementarios:** SUP-I01 y SUP-SEC02.
- **Restricciones:** ADR-0030; una carpeta de descargas, una sola cola.
- **Dependencias:** UC-09, UC-10 y UC-26; D-11 y D-15.

## Criterios de aceptación

1. `files delete` sin `--confirm` nunca borra nada.
2. Ningún archivo sin reclamación propia cambia (tamaño, fecha y SHA-256), aunque esté en la misma carpeta.
3. Un resultado que falta se informa sin cambiar el estado del job.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Vista previa, confirmación, archivos ajenos en la misma carpeta | Cualquier sistema |
| Resultados que faltan, huérfanos y espacio usado | Cualquier sistema |
| Archivo abierto por otro proceso al borrar | **Windows** |
