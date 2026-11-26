# ADR-0030: Propiedad de los archivos finales mediante reclamaciones

- **Estado:** Aceptada; validación en Windows pendiente (campaña T42, paso 11)
- **Fecha:** 2026-11-26 (revisada en T50 el mismo día: identidad del dueño, base de datos restaurada, migración 0004)
- **Origen:** auditoría previa a la aceptación (T49), §7; riesgo R-14 de la [lista de riesgos](../project-management/risk-list.md)
- **Complementa:** T44 (carpeta de parciales por job e índice `unique_output_path`, migración 0003)

## Contexto

Con una plantilla sin `%(id)s` o un título recortado por `max_filename_length`, dos contenidos pueden recibir el mismo nombre final. T44 dio a cada job su carpeta de parciales y un índice único sobre `output_path`, pero el índice solo actúa cuando el segundo job ya publicó `JobCompleted`. Para entonces yt-dlp 2026.10.26 ya trató el archivo del otro job como "ya descargado" (`YoutubeDL.process_info`) y, aun así, ejecutó `fixup()` y `post_process()` sobre él; `FFmpegExtractAudioPP` sobrescribe su destino por defecto (`nopostoverwrites=False`). Además, un archivo que no escribió ningún job de la cola (del usuario, de una versión anterior o de un job purgado) se tomaba como resultado propio y el job quedaba `COMPLETED` con él; en el entorno de desarrollo se reprodujo este último caso.

Los postprocessors `before_dl` se ejecutan en `process_info` antes de la búsqueda del archivo existente, así que son el punto en que todavía no se ha tocado nada.

## Decisión

Cada job de descarga **reclama su nombre final antes de descargar**, con el postprocessor `OutputOwnershipGuard` (`before_dl`):

- **Qué se reclama:** la ruta final sin extensión (carpeta final + nombre base), canonizada con `os.path.realpath` y `os.path.normcase`. La extensión cambia al unir formatos o al extraer el audio. En Windows, mayúsculas y separadores no crean otro nombre, como en NTFS. No se normaliza Unicode, porque NTFS y ext4 tampoco lo hacen.
- **Cómo:** un archivo `<sha256>.claim` en `state/output-claims/`, creado con `O_CREAT | O_EXCL` (atómico en NTFS y en sistemas POSIX locales), que contiene el **owner token** del job: su id y el instante en que el job store lo guardó (`Job.owner_token`). El hash fija la longitud y evita los límites de ruta.
- **Reglas:**
  1. Si la reclamación es de otro job, el job falla con `FILESYSTEM` sin tocar nada y el mensaje nombra al dueño.
  2. Si la reclamación es nueva y ya existe en la carpeta final un archivo con ese nombre base (cualquier extensión), el archivo no es del job: falla con `FILESYSTEM` y suelta la reclamación.
  3. Si la reclamación ya era del job, el archivo existente es suyo (cierre tras moverlo y antes de registrar `JobCompleted`, UC-06): se completa sin descargar.
- **Vida de la reclamación:** se conserva mientras el job es dueño del archivo; se suelta si el job falla o se cancela sin dejar su archivo final, y cuando `purge` borra el job (UC-10). Tras purgar, el archivo sigue protegido por la regla 2.
- El índice `unique_output_path` se mantiene como segunda defensa. Un archivo que varios jobs de E1 reclamaban a la vez no tiene dueño demostrable: la migración 0004 pasa a todos esos jobs a `FAILED` (reintentables), sin `output_path`, con un diagnóstico que nombra el archivo y a todos los jobs, y no toca el archivo. (La 0003, tal como se publicó, se lo daba al id menor; la 0004 lo deshace.)
- **Carpetas de parciales:** `.partial/job-<id>` guarda el owner token en `.owner`. Un job solo reanuda desde una carpeta suya; otra con el mismo id (de un job perdido) se aparta como `orphan-job-<id>-<instante>` con todo su contenido, y la descarga empieza de cero. `purge` solo borra carpetas del job purgado.

### Base de datos restaurada de una copia anterior

Restaurar una copia antigua de `queue.sqlite3` no es una operación soportada, pero no puede perder datos en silencio. Al restaurarla, SQLite vuelve a dar los ids de los jobs perdidos (los creados después de la copia) a jobs nuevos. Con el owner token:

- Un job nuevo nunca toma la reclamación ni el archivo final de un job perdido: falla con `FILESYSTEM` y el mensaje sugiere que la base de datos se restauró.
- Un job nuevo nunca reanuda desde los parciales de un job perdido (el resultado sería un archivo corrupto): los aparta, intactos.
- Un job de la copia que reaparece (mismo id y mismo instante de creación) es el mismo job: reconoce su reclamación y su archivo, como tras un cierre (UC-06 A4).
- `purge` suelta las reclamaciones de los jobs perdidos; sus archivos siguen protegidos por la regla 2.
- Un job `COMPLETED` cuyo archivo ya no existe no provoca ninguna acción sobre archivos.

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

Ninguna de estas situaciones permite que un job modifique o borre el archivo de otro job o del User por la vía de la reclamación; lo que no se garantiza es que la colisión se detecte antes de descargar.

- **Una carpeta de descargas tiene una sola autoridad:** una cola (un `state_directory`). Dos colas que comparten carpeta no ven sus reclamaciones. Aun así, la regla 2 sigue protegiendo los archivos ya terminados de la otra cola; la carrera que no se cubre es la de dos jobs, uno de cada cola, descargando a la vez el mismo nombre.
- **Restaurar una copia antigua de la base de datos** no se soporta como operación de copia de seguridad: los jobs perdidos se pierden. Sí es seguro (sección anterior): no se apropia, modifica ni borra ningún archivo, y los parciales de los jobs perdidos se conservan apartados.
- Carpetas de descargas en recursos de red (SMB) o en sistemas de archivos sin `O_EXCL` atómico.
- Carpetas NTFS con distinción de mayúsculas activada por directorio (`fsutil file setCaseSensitiveInfo`): `normcase` las trata como si no distinguieran.
- Equivalencias de mayúsculas fuera de `str.lower()` de Python (la tabla de NTFS puede diferir en caracteres poco comunes).

## Validación

- **Linux:** pruebas unitarias de `OutputClaims` y de extremo a extremo con colas reales (`tests/command_line/test_output_ownership.py`), con huella de tamaño, fecha y SHA-256 del archivo protegido.
- **Restauración de una copia (T50):** reclamación y parciales de un job perdido con el mismo id, en la MediaSource real; purge con una carpeta ajena; migración 0004 desde las versiones 2 y 3.
- **Windows (pendiente, T42):** pruebas `windows` de mayúsculas y separadores, archivo existente con otra capitalización, ruta de más de 260 caracteres y archivo abierto por otro proceso; paso 11 de la campaña.
