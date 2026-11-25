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
2. **Borrado de parciales por nombre base.** T32 borraba cualquier `.part` o `.ytdl` con el mismo nombre base que el archivo final. El nombre base no identifica al job (siguiente sección). Ahora solo se borran los nombres que yt-dlp da al formato anterior (`YoutubeDL.process_info`): `<base>.<ext>.part` si era un formato único y `<base>.f<id>.<ext>.part` por cada parte de uno unido (`137+140`), más sus `.ytdl`.

### Seguridad del borrado de parciales

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
