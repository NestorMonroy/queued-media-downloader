# ADR-0030: Propiedad de los archivos finales mediante reclamaciones

- **Estado:** Aceptada; validación en Windows pendiente (campaña T42, paso 11)
- **Fecha:** 2026-11-26
- **Origen:** auditoría previa a la aceptación (T49), §7; riesgo R-14 de la [lista de riesgos](../project-management/risk-list.md)
- **Complementa:** T44 (carpeta de parciales por job e índice `unique_output_path`, migración 0003)

## Contexto

Con una plantilla sin `%(id)s` o un título recortado por `max_filename_length`, dos contenidos pueden recibir el mismo nombre final. T44 dio a cada job su carpeta de parciales y un índice único sobre `output_path`, pero el índice solo actúa cuando el segundo job ya publicó `JobCompleted`. Para entonces yt-dlp 2026.10.26 ya trató el archivo del otro job como "ya descargado" (`YoutubeDL.process_info`) y, aun así, ejecutó `fixup()` y `post_process()` sobre él; `FFmpegExtractAudioPP` sobrescribe su destino por defecto (`nopostoverwrites=False`). Además, un archivo que no escribió ningún job de la cola (del usuario, de una versión anterior o de un job purgado) se tomaba como resultado propio y el job quedaba `COMPLETED` con él; en el entorno de desarrollo se reprodujo este último caso.

Los postprocessors `before_dl` se ejecutan en `process_info` antes de la búsqueda del archivo existente, así que son el punto en que todavía no se ha tocado nada.

## Decisión

Cada job de descarga **reclama su nombre final antes de descargar**, con el postprocessor `OutputOwnershipGuard` (`before_dl`):

- **Qué se reclama:** la ruta final sin extensión (carpeta final + nombre base), canonizada con `os.path.realpath` y `os.path.normcase`. La extensión cambia al unir formatos o al extraer el audio. En Windows, mayúsculas y separadores no crean otro nombre, como en NTFS. No se normaliza Unicode, porque NTFS y ext4 tampoco lo hacen.
- **Cómo:** un archivo `<sha256>.claim` en `state/output-claims/`, creado con `O_CREAT | O_EXCL` (atómico en NTFS y en sistemas POSIX locales), que contiene el id del job. El hash fija la longitud y evita los límites de ruta.
- **Reglas:**
  1. Si la reclamación es de otro job, el job falla con `FILESYSTEM` sin tocar nada y el mensaje nombra al dueño.
  2. Si la reclamación es nueva y ya existe en la carpeta final un archivo con ese nombre base (cualquier extensión), el archivo no es del job: falla con `FILESYSTEM` y suelta la reclamación.
  3. Si la reclamación ya era del job, el archivo existente es suyo (cierre tras moverlo y antes de registrar `JobCompleted`, UC-06): se completa sin descargar.
- **Vida de la reclamación:** se conserva mientras el job es dueño del archivo; se suelta si el job falla o se cancela sin dejar su archivo final, y cuando `purge` borra el job (UC-10). Tras purgar, el archivo sigue protegido por la regla 2.
- El índice `unique_output_path` se mantiene como segunda defensa. La migración 0003 libera, al actualizar una base de datos de E1, los archivos que dos jobs reclamaban a la vez: los conserva el job de id menor y los demás pasan a `FAILED` (reintentables).

## Alternativas descartadas

- **Detectar después, con el índice único (T44):** llega tarde (§ Contexto).
- **Bloqueo de archivos de Windows:** descartado por el Responsable como garantía de aislamiento; además no existe en el momento de la decisión.
- **Reclamación junto al archivo final (`<final>.claim`):** deja archivos visibles en la carpeta de descargas de cada playlist.
- **Reclamación en `download_directory/.partial`:** dos jobs con distinta carpeta de descargas y la misma ruta final, o con una plantilla absoluta, no se verían.
- **`nopostoverwrites=True` y `--no-overwrites`:** solo cubren a un postprocessor y no evitan que el job tome como suyo un archivo ajeno.

## Consecuencias

- Ningún job sobrescribe, borra ni modifica el archivo final de otro, ni toma como suyo un archivo que no escribió.
- Cambio de comportamiento: volver a encolar un contenido cuyo archivo ya existe en la carpeta final (por ejemplo, tras purgar su job) termina en `FAILED` con `FILESYSTEM` y la indicación de mover el archivo o usar `%(id)s`, en lugar de `COMPLETED` sin descargar.
- Un job cancelado por terminación forzada (UC-05 A2) no llega a soltar su reclamación; la suelta `retry` (la vuelve a usar el mismo job) o `purge`.

## Restricciones (escenarios no soportados)

- Dos colas distintas (dos `state_directory`) que comparten carpeta de descargas no se ven entre sí.
- Carpetas de descargas en recursos de red (SMB) o en sistemas de archivos sin `O_EXCL` atómico.
- Carpetas NTFS con distinción de mayúsculas activada por directorio (`fsutil file setCaseSensitiveInfo`): `normcase` las trata como si no distinguieran.
- Equivalencias de mayúsculas fuera de `str.lower()` de Python (la tabla de NTFS puede diferir en caracteres poco comunes).

## Validación

- **Linux:** pruebas unitarias de `OutputClaims` y de extremo a extremo con colas reales (`tests/command_line/test_output_ownership.py`), con huella de tamaño, fecha y SHA-256 del archivo protegido.
- **Windows (pendiente, T42):** pruebas `windows` de mayúsculas y separadores, archivo existente con otra capitalización, ruta de más de 260 caracteres y archivo abierto por otro proceso; paso 11 de la campaña.
