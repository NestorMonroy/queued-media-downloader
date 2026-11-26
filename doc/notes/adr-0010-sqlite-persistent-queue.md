# ADR-0010: Cola persistente en SQLite

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** los términos vigentes (`selected_format_id`, `job_requests`) están en [ADR-0014](adr-0014-use-case-structure-and-vocabulary.md).

## Contexto

En equipos con conexión lenta, volver a descargar lo ya descargado es el desperdicio más caro. yt-dlp reanuda descargas a nivel de archivo (`continuedl` con `.part`; `.ytdl` en descargas fragmentadas) y evita repetir videos con `download_archive`, pero no conoce la existencia de una cola.

Al reanudar, las URLs de descarga (que caducan en horas) se vuelven a extraer. El archivo parcial solo sirve si el nombre de salida y el formato coinciden con la primera ejecución.

## Decisión

- La cola se persiste en **SQLite**: trabajos, tipo (expansión o descarga), estado, opciones, relación padre-hijo y contexto de playlist.
- Se guarda el **`format_id` elegido** en la primera extracción y se solicita explícitamente al reanudar.
- **Un solo escritor:** solo el proceso principal escribe en SQLite; los workers emiten eventos ([ADR-0008](adr-0008-process-based-worker-pool.md)).
- Restricción única por `(extractor_key, id)` para evitar duplicados ([ADR-0009](adr-0009-playlist-expansion-into-jobs.md)).

## Consecuencias

- Al arrancar, los trabajos pendientes o interrumpidos se vuelven a encolar.
- El nombre de salida debe ser determinista entre ejecuciones (el `outtmpl` lo construye el proyecto).
- SQLite viene con Python: no añade dependencias.
- Pendiente de diseño: esquema de tablas, estados y transiciones.

## Seguimiento de T32: reanudación verificada (2026-11-25)

La reanudación usa lo que yt-dlp ya hace: `continuedl` continúa el `.part` con una petición `Range`. El proyecto solo añade lo que yt-dlp no sabe: qué formato pidió el primer intento y qué hacer si ya no existe (UC-06 A1).

### Qué queda probado

| Garantía | Prueba |
|---|---|
| Al reanudar solo se descargan los bytes que faltan. La única otra petición es la extracción (yt-dlp vuelve a extraer la URL; con un enlace directo, el extractor genérico lee 512 bytes) | `test_interrupted_download_continues_from_its_partial_file`: lista exacta de peticiones `[(/sample.mp4, None), (/sample.mp4, bytes=5000-)]` |
| El archivo final es idéntico al original | La misma prueba compara los bytes |
| El reintento usa el format selector original, y solo una vez | `test_unavailable_saved_format_is_retried_once_with_the_original_selector` y `test_failed_retry_publishes_one_failure_and_is_not_retried_again`: formatos pedidos `["999", "bv*+ba/b"]` y `["999", "777"]` |
| El nuevo formato queda guardado | `test_recovered_job_with_an_unavailable_format_finishes_with_a_new_one`: job recuperado de SQLite, `selected_format_id` pasa de `999` a `mp4` |
| Un fallo que no es de formato no reintenta | `test_other_failure_with_a_saved_format_is_not_retried`: un solo intento |
| La detección depende de un texto de yt-dlp, comprobado con la versión fijada | `test_yt_dlp_format_error_contract.py`: la versión de `pyproject.toml`, la instalada y la verificada coinciden; el error real de yt-dlp se detecta; otros errores no |
| No se publica `JobCompleted` sin un archivo final no vacío | `test_download_without_an_output_file_is_not_completed`, `test_download_whose_output_file_is_empty_is_not_completed` |
| Volver a descargar un job terminado no descarga nada y termina igual | `test_finished_download_run_again_completes_without_downloading` |

### Defectos hallados y corregidos

1. **Clasificación de un reintento fallido.** El reintento se ejecutaba dentro del `except` del primer intento. yt-dlp tomaba el primer error como causa del segundo (`sys.exc_info()`) y el fallo quedaba `UNKNOWN` en lugar de `UNAVAILABLE`. El reintento se hace fuera del `except`, y el clasificador quita también los `DownloadError` anidados.
2. **Borrado de parciales por nombre base.** T32 borraba cualquier `.part` o `.ytdl` con el mismo nombre base que el archivo final, y el nombre base no identifica al job. La revisión lo restringió a los nombres del formato abandonado. **T44 lo sustituye** por una carpeta de parciales por job (siguiente sección).

### Seguridad del borrado de parciales (análisis de T32, superado por T44)

| Escenario | Garantía |
|---|---|
| Varios jobs del mismo video y el mismo tipo de salida | Imposible: el índice único `unique_active_download_per_media` admite un solo job no `SKIPPED` por `(extractor, id, audio_only)`, también terminado o fallido |
| El mismo video como video y como solo audio | Carpetas distintas (`audio\`, T23): la limpieza solo mira la carpeta del archivo final |
| Formatos distintos del mismo video | Solo se borran los del formato que el sitio ya no ofrece; los de otro formato se conservan (`test_parts_of_other_formats_with_the_same_name_are_kept`) |
| Descargas concurrentes del mismo job | Imposible: un job `RUNNING` no vuelve a enviarse, y la descarga y la limpieza ocurren en el mismo worker, una tras otra |
| Nombre base compartido por **otro** job | Posible: un título largo recortado por `max_filename_length` pierde el `[id]`; una plantilla sin `%(id)s`; dos extractores con el mismo id y el mismo título. Solo se borraría un parcial de ese otro job si además usa el mismo id de formato. Consecuencia: ese job pierde lo descargado y empieza de cero; nunca se toca un archivo terminado. Riesgo R-14 |
| Archivo abierto por otro worker (Windows) | Windows no permite borrar un archivo abierto sin `FILE_SHARE_DELETE`, y yt-dlp abre el `.part` con `open()`. El error se registra y el archivo se conserva (`test_file_that_cannot_be_removed_is_kept_without_failing`) |
| Archivo borrado por otro mientras tanto | Se ignora (`test_file_removed_by_someone_else_meanwhile_is_ignored`) |
| Limpieza repetida | Sin efectos (`test_repeating_the_cleanup_removes_nothing_more`) |
| Interrupción durante la limpieza | Ver la siguiente sección |

### Consistencia ante una interrupción

El orden dentro del worker es: primer intento → `FormatSelected` del reintento → descarga → comprobación del archivo final → limpieza → `JobCompleted`. Solo el proceso principal escribe en SQLite, en el orden en que llegan los mensajes.

| Interrupción | Estado guardado | Qué hace el siguiente `run` |
|---|---|---|
| Antes del `FormatSelected` del reintento | `RUNNING`, formato antiguo | Recupera a `PENDING`; repite el primer intento y el reintento (A1). Consistente |
| Tras `FormatSelected`, durante la descarga | `RUNNING`, formato nuevo | Reanuda el `.part` del formato nuevo. Los parciales del antiguo quedan en disco: ya no se sabe qué formato era |
| Tras la descarga, antes o durante la limpieza | `RUNNING`, formato nuevo, archivo final completo | Vuelve a descargar con el formato nuevo: yt-dlp ve el archivo terminado y no descarga nada (`test_finished_download_run_again_completes_without_downloading`); el job termina `COMPLETED`. Los parciales antiguos que no se borraron quedan en disco |
| Tras `JobCompleted` | `COMPLETED` | Nada |

En ningún caso se publica un resultado satisfactorio sin el archivo final, ni se pierde lo descargado del formato vigente. Lo único que puede quedar son parciales del formato abandonado, ocupando disco, si el cierre cae en esa ventana. Guardar el formato abandonado para limpiarlo después sería un mecanismo nuevo para un efecto que no compromete el resultado; no se añade.

### Simulación y recuperación real

Las pruebas crean el `.part` que deja una interrupción en lugar de interrumpir un proceso. Demuestran la reanudación en condiciones controladas, no la recuperación ante un cierre real del sistema. Esa demostración depende de terminar el worker y sus descendientes (slice C) y queda como criterio obligatorio de E2: [plan de E2, §5.1](../project-management/iteration-plan-e2.md#51-criterio-obligatorio-de-integración-entre-los-slices-b-y-c).


## Seguimiento de T44: propiedad de los archivos de cada job (2026-11-25)

El Responsable no aceptó el riesgo residual de T32 (R-14): borrar el parcial de otro job que comparte nombre base es un defecto de aislamiento, aunque el archivo final quede intacto. Tampoco vale el bloqueo de archivos de Windows como garantía.

### Decisión

La arquitectura ya tenía las dos primitivas necesarias:

1. **Una identidad persistente:** el id del job. La migración 0003 lo hace `AUTOINCREMENT`, para que SQLite no vuelva a dar el id de un job borrado (`purge`, UC-10).
2. **Una carpeta temporal por descarga en yt-dlp:** `paths.temp`. yt-dlp escribe ahí todo lo intermedio (`.part`, `.ytdl`, partes `.f<id>`, `.temp` de la unión) y solo mueve el archivo terminado a la carpeta final, después de todos los postprocessors (`YoutubeDL.post_process`: `post_process` → `MoveFilesAfterDownloadPP` → `after_move`). También comprueba ahí si el archivo ya existe (`existing_video_file(full_filename, temp_filename)`).

Cada job descarga con `paths.temp = <carpeta de descargas>/.partial/job-<id>` (`Job.partial_directory`). Todo lo que contiene esa carpeta es del job por construcción, sea cual sea el nombre de los archivos. La limpieza es borrar la carpeta del job tras una descarga terminada, sin buscar nombres. Está dentro de la carpeta de descargas para que mover el archivo final sea renombrarlo, sin copiarlo entre unidades.

Además, el índice único `unique_output_path` impide que dos jobs reclamen el mismo archivo final. Si dos contenidos distintos dan el mismo nombre final (plantilla sin `%(id)s`, título recortado), yt-dlp toma el segundo por "ya descargado" y devuelve la ruta del primero. Antes de T44 ese job quedaba `COMPLETED` con el archivo de otro. Ahora queda `FAILED` (`FILESYSTEM`) con un mensaje que pide una plantilla con `%(id)s`.

### Garantías

| Escenario | Garantía | Prueba |
|---|---|---|
| Nombres truncados por `max_filename_length` | Cada job escribe en su carpeta; la limpieza de uno no ve los archivos de otro | `test_completion_never_touches_partial_files_of_another_job[trimmed name]` (comprueba que la colisión de nombres ocurre) |
| Plantilla sin `%(id)s` | Igual | `…[template without id]` |
| El mismo id de formato en dos jobs | Igual: la carpeta, no el nombre, decide | Las dos anteriores abandonan el formato `999` |
| Archivo final compartido por dos jobs | El segundo queda `FAILED`, nunca `COMPLETED` con el archivo del otro | `test_job_whose_output_file_belongs_to_another_job_fails`, `test_second_job_claiming_the_same_output_file_is_rejected`, `test_two_jobs_cannot_own_the_same_output_file` |
| Descargas concurrentes | Un job se ejecuta en un solo worker a la vez; cada job tiene su carpeta | — |
| Formatos abandonados (A1) | Se van con la carpeta al terminar | `test_unavailable_saved_format_is_retried_once_with_the_original_selector` |
| Interrupción entre el formato nuevo y la limpieza | La siguiente descarga terminada del mismo job borra la carpeta, con lo que quedara | `test_leftovers_of_an_interrupted_cleanup_go_with_the_next_completion` |
| Id reutilizado tras `purge` | Imposible (`AUTOINCREMENT`) | `test_job_ids_are_never_reused_after_deleting_the_last_job` |
| Limpieza repetida o carpeta ausente | Sin efectos | Mismas pruebas (la segunda descarga no encuentra la carpeta) |
| La carpeta no se puede borrar | Se registra; la descarga ya terminó y queda `COMPLETED`. Se borra en la siguiente descarga terminada del job o al purgarlo (T48) | — |
| Carpeta común `.partial` | No se borra: otro worker puede estar creando la suya dentro | — |

### Cuándo se publica `JobCompleted`

Una ruta registrada no basta. Se publica solo si:
1. `YoutubeDL.download` terminó sin excepción y devolvió `0` (con la configuración del proyecto, yt-dlp lanza una excepción ante cualquier error; el código se comprueba igualmente);
2. hay una ruta registrada en `after_move`, que yt-dlp solo alcanza tras todos los postprocessors y tras mover el archivo;
3. la ruta está fuera de la carpeta de parciales y el archivo existe y no está vacío.

Pruebas: `test_download_with_a_non_zero_return_code_is_not_completed`, `test_failed_postprocessing_is_not_completed`, `test_output_file_left_in_the_partial_directory_is_not_completed`, `test_download_without_an_output_file_is_not_completed`, `test_download_whose_output_file_is_empty_is_not_completed`.

### Consecuencias

- Un `.part` anterior a T44, en la carpeta de descargas, no se reanuda: la descarga vuelve a empezar. No hay versiones publicadas, así que no afecta a ningún usuario.
- La carpeta `.partial` aparece en la carpeta de descargas; en Windows no se oculta por empezar con un punto.
- `purge` (T48) debe borrar la carpeta de parciales de los jobs que purga: con ids que no se reutilizan, nadie más la borraría.
- La propiedad de los archivos ya no depende del bloqueo de archivos de Windows.

## Seguimiento de T49: reclamación del nombre final y migraciones (2026-11-26)

- El índice `unique_output_path` detectaba la colisión cuando el segundo job ya había tratado el archivo del primero como "ya descargado". La propiedad del archivo final se decide ahora antes de descargar, con una reclamación exclusiva ([ADR-0030](adr-0030-final-file-ownership-claims.md)); el índice queda como segunda defensa.
- Una migración fallida se deshace y su conexión se cierra; la 0003 se corrigió para poder aplicarse a una base de E1 con un archivo reclamado por dos jobs (diseño, Parte 2, §2.5).
