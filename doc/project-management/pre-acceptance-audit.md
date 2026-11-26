# Auditoría integral previa a la aceptación (T49)

- **Fecha:** 2026-11-26
- **Rol que la ejecuta:** Agente de implementación (entorno Linux)
- **Base auditada:** `main` = `origin/main` = `7d54511` al empezar
- **Instrucción:** "Auditoría integral de completitud…", versión 1.0.0, del Responsable del proyecto
- **Resultado:** `IMPLEMENTATION_COMPLETE`, `DEVELOPMENT_VERIFICATION_PASSED`, `WINDOWS_VALIDATION_PENDING`, `FINAL_ACCEPTANCE_PENDING` → **`READY_FOR_WINDOWS_VALIDATION`**

Este documento recoge los hallazgos y lo que se hizo con cada uno. No repite la trazabilidad: la matriz por escenario y por requisito está en el [plan de E2, §8](iteration-plan-e2.md#8-matriz-de-casos-de-uso-implementación-y-validación), y los riesgos en la [lista de riesgos](risk-list.md).

## 1. Decisiones aprobadas y cómo quedaron

| Decisión del Responsable | Implementación | Pruebas | Documentos |
|---|---|---|---|
| `Ctrl+C` no cancela: estado y parciales se conservan; código 130 | Ya cumplida (T39). T49 añade: los `Ctrl+C` posteriores al segundo se ignoran hasta salir; el manejador cubre el arranque y el apagado del pool; un `Ctrl+C` durante el apagado ordenado termina los árboles | `SIGINT` real: uno, dos y seis seguidos (sin traza, job `RUNNING`, reanudación) | UC-05 A6, UC-06 A5, diseño §4.1, vocabulario (*interruption*), T39 corregida en el plan |
| `purge` sin opciones = `COMPLETED` + `CANCELLED`; nunca borra archivos finales; conserva playlists con trabajo pendiente | Ya cumplida (T48). T49: primero la base de datos (con la cola ocupada no se toca nada) y suelta reclamaciones huérfanas | Combinaciones (entrada `CANCELLED` con `--completed`, `FAILED`, `RUNNING`); cola ocupada | UC-10 completo (contrato), vocabulario §1.1, diseño §4.1 |
| `retry` de una playlist incluye entradas `FAILED`/`CANCELLED`, nunca `COMPLETED`; sin duplicados | Ya cumplida (T45) | Nueva: idempotencia con peticiones repetidas, `attempt_count`, cada entrada descargada una vez, duplicados `SKIPPED` | UC-07 completo (A3, A4) |
| Cancelar un `FAILED` lo deja igual | Ya cumplida | Nueva: `run` procesa `CANCEL` de `COMPLETED`, `FAILED`, `SKIPPED` y `CANCELLED` sin cambiar nada (también el motivo del fallo) | UC-05 A7, vocabulario §1.1 (terminado / reintentable / cancelable) |

## 2. Defectos encontrados y corregidos

| # | Defecto | Sección | Corrección (commit) | Prueba de regresión |
|---|---|---|---|---|
| D-01 | Un job tomaba como suyo un archivo final ajeno (de otro job, del User o de un job purgado) y yt-dlp le aplicaba `fixup` y postprocessors | §7 | Reclamación del nombre antes de descargar, [ADR-0030](../notes/adr-0030-final-file-ownership-claims.md) (`f0deeb8`) | `tests/command_line/test_output_ownership.py`, `tests/media_extraction/test_output_claims.py` y 3 de `test_yt_dlp_media_source.py` |
| D-02 | Una migración fallida dejaba la transacción abierta y la conexión sin cerrar | §9 | Rollback y cierre (`036f87d`) | `test_a_failing_migration_leaves_the_database_as_it_was_and_closed` |
| D-03 | La migración 0003 no se podía aplicar a una base de E1 con un archivo reclamado por dos jobs: la cola no se abría | §9 | Corrección de la 0003, única excepción documentada en el diseño §2.5 (`036f87d`) | `test_migration_3_releases_a_file_claimed_twice_by_version_2_jobs` |
| D-04 | Una base de datos inutilizable (migración rota, archivo que no es SQLite) terminaba con una traza | §9 | `JobStoreUnavailableError`, mensaje con ruta y causa, código 1 (`4849e7a`) | `tests/command_line/test_unusable_database.py` |
| D-05 | `cancel`, `retry` y `purge` con la base de datos ocupada terminaban con una traza; `purge` borraba antes los parciales | §5 (UC), §9 | Traducción en la raíz de composición, informe central en `main`, `purge` con la base de datos primero (`7cfb360`) | `test_every_writing_command_reports_a_busy_queue_without_changing_it` |
| D-06 | Un tercer `Ctrl+C` interrumpía el apagado inmediato; uno tras restaurar el manejador mataba el proceso con traza | §10, decisión 1 | `89f4ba6` | `test_more_ctrl_c_while_stopping_at_once_are_ignored`, `tests/command_line/test_console_interruption.py` |
| D-07 | `Job.complete` aceptaba una descarga sin ruta; un doble de prueba (`JobCompleted(output_path=None)` para una descarga) no representaba al worker real | §8 | Contrato por tipo de job; el applier convierte un incumplimiento en `FAILED`; el doble distingue video y solo audio (`0c81d54`) | `test_a_download_cannot_complete_without_its_output_file`, `test_a_completion_that_breaks_the_contract_fails_the_job` |
| D-08 | Solo las pruebas de comandos estaban aisladas: otras pruebas escribieron en la cola y la carpeta de descargas reales (T45, T46) | §5 | Aislamiento autouse para todas y huella de los datos reales antes y después de la sesión (`ccf526f`) | `tests/test_real_environment_guard.py` y una prueba de fuga sobre un `HOME` ficticio (§4) |
| D-09 | No había un ejecutor de las cinco comprobaciones con stop-on-error | §13 | `scripts/run_checks.py` (`d1aafdb`) | Uso en cada commit de T49 |
| D-10 | UC-07 a UC-10 solo tenían una especificación breve | §4 | Especificaciones completas | — |

**Incidencia de proceso durante la auditoría:** el commit de la migración se creó una vez sin ejecutar antes las comprobaciones (formato y tipos fallaban). Se detectó con `run_checks.py` antes de publicar, se corrigió y se rehízo el commit local (no publicado) con la identidad establecida; desde entonces cada commit se hizo solo tras `run_checks.py` con código 0.

## 3. Calificación de los casos de uso (§4)

Los diez casos de uso tienen ahora especificación completa: flujos básico y alternativos, excepciones, precondiciones y postcondiciones (éxito y fallo), transiciones, contrato del comando cuando aplica, restricciones y escenarios de prueba con su plataforma. Cambios principales:

- **UC-01:** A8 (base de datos inutilizable o migración fallida).
- **UC-02:** `--playlist` en el flujo; A3 atómico; A4.
- **UC-03:** A7 (nombre final ajeno), A8 (sin archivo final utilizable y contrato de `JobCompleted`), A9 (`Ctrl+C`); postcondiciones con la subcarpeta de audio, la carpeta de la playlist y la reclamación.
- **UC-04:** A6 alineado con UC-07 A3; A7 (lotes tardíos); postcondición de fallo.
- **UC-05:** A6 como interrupción; A7 con `FAILED`; A8; excepciones; contrato; transiciones.
- **UC-06:** A4 a A7; transiciones; restricciones.
- **UC-07 a UC-10:** documentos nuevos.

## 4. Aislamiento de las pruebas (§5)

### Auditoría

| Elemento | Riesgo encontrado | Estado |
|---|---|---|
| Fixtures de `tests/command_line/` | Aisladas (autouse desde T46) | Sustituidas por la fixture raíz |
| `downloaded_playlist` y `test_completed_job_is_not_retried` | Escribieron en la cola y las descargas reales en T45/T46 | Corregido entonces; ahora cubierto por la fixture raíz |
| Pruebas fuera de `command_line/` que llaman a `load_command_settings` | Leían el `config.toml` real de la raíz del proyecto | `CONFIG_FILE_NAME` apunta a un `config.toml` de la prueba |
| Pruebas con subprocesos (`run` real, `-m queued_media_downloader`) | Heredan el entorno: con la fixture raíz, el estado y las descargas de la prueba; pero leerían un `config.toml` real | La sesión se detiene si existe `config.toml` en la raíz |
| Workers reales (`spawn`) | Reciben la configuración del proceso principal | Aislados |
| Dobles (`InMemoryJobStore`, `ScriptedWorkerPool`, `FakeMediaSource`…) | No tocan disco salvo `tmp_path` | Aislados |
| Procesos ajenos | Las pruebas del terminador solo terminan árboles que ellas mismas crean (`start_tree`) | Aislados |
| Logs | Van a `state_directory/logs`, que es el de la prueba | Aislados |
| `scripts/experiments/process_tree_termination.py` | Crea sus árboles en una carpeta temporal | Sin cambios |
| Pruebas `network` | Usan `tmp_path` | Aisladas |

### Regresión

`tests/conftest.py` toma, al empezar y al terminar la sesión, la huella de cada archivo bajo `project_root()/state`, `~/Downloads/queued-media-downloader` y `config.toml` (ruta, tamaño, fecha en ns y SHA-256) y hace fallar la sesión con la lista de archivos creados, borrados o cambiados. Compara contenido, no recuentos: `test_a_change_that_keeps_size_and_count_is_still_detected` cambia un archivo sin cambiar su tamaño ni su fecha y se detecta. La protección se comprobó de extremo a extremo con una prueba de fuga temporal que escribía en `~/Downloads/queued-media-downloader` bajo un `HOME` ficticio (`/tmp/fakehome`): la sesión terminó con código 1 y `created: downloads/leak.txt`. La prueba de fuga se borró después; nunca se escribió en las carpetas reales.

### Evaluación de la limpieza anterior y estado de los datos reales

Lo que se sabe, con evidencia de solo lectura del 2026-11-26:

- **Cola real** (`state/queue.sqlite3`): 22 jobs (ids 1 a 22). Todas sus URL son de servidores locales `127.0.0.1` de las pruebas y todos están `COMPLETED` o `SKIPPED`; 18 se actualizaron el 2026-11-25 desde las 21:39. Es decir, **también esas filas las crearon ejecuciones de pruebas**. El archivo principal no cambia desde 2026-11-25 23:20:04 UTC.
- **Limpieza de T46:** se borraron los jobs con id ≥ 23 creados desde 2026-11-25T23:00 (12 filas directas; las borradas en cascada no se contaron) y las carpetas `Local feed` y `.partial` de la carpeta de descargas real. No había una copia previa, así que **no se puede demostrar que el estado anterior a las fugas se haya preservado**; solo que lo que queda no contiene, en apariencia, datos de uso real (ninguna URL que no sea local).
- **Log real** (`state/logs/queued-media-downloader.log`, 116 líneas): la primera entrada es de 2026-11-23 22:48 y todas las URL son locales; se escribió por última vez el 2026-11-25 a las 23:19. Las pruebas de E1 y de T45–T46 añadieron líneas.
- **Descargas reales:** solo `sample [sample].mp4` (16 396 bytes, 2026-11-23), con el nombre del medio de prueba; no cambió.
- **Efecto de la propia inspección:** abrir la base de datos en solo lectura actualizó la fecha de los archivos auxiliares de WAL (`queue.sqlite3-shm`, `-wal`); el contenido de la base de datos no cambió. Desde la protección de T49, ninguna sesión de pruebas ha cambiado los datos reales.
- No se borró ningún dato real durante esta auditoría.

## 5. R-14: calificación por escenario (§6)

| Escenario | Comportamiento | Evidencia |
|---|---|---|
| Identidad de un job e ids reutilizados | `AUTOINCREMENT` y `sqlite_sequence` sembrado: un id purgado no se reutiliza | `test_job_ids_are_never_reused_after_deleting_the_last_job` |
| Migraciones (0 → 3, 1 → 3, 2 → 3) | Datos, enlaces, peticiones e índices conservados; integridad referencial | `tests/job_storage/test_sqlite_connection.py` |
| Base de E1 con un archivo reclamado dos veces | En T49, el id menor lo conservaba; **corregido en T50**: ningún dueño (migración 0004) | Pruebas de las migraciones 3 y 4 |
| Base de datos nueva | Esquema 3 y reclamaciones vacías | Pruebas de conexión y de comandos |
| **Base de datos restaurada de una copia anterior** | En T49 quedó como restricción manual. **Corregido en T50:** owner token (id e instante de creación) en reclamaciones y parciales; nada se apropia ni se pierde | Pruebas de T50 (ADR-0030) |
| Configuraciones distintas entre jobs | Cada job guarda sus download options; las reclamaciones dependen solo de la ruta final canónica | Pruebas de reclamaciones |
| Carpeta de descargas compartida por dos colas | **No soportado** (restricción de ADR-0030) | — |
| Parciales de versiones anteriores (junto al archivo final, E1) | No se reutilizan ni se borran: cada job usa `.partial/job-<id>`; un archivo final de E1 con el mismo nombre se protege (regla 2) | `test_completion_never_touches_partial_files_of_another_job`, `test_a_file_the_queue_did_not_write_is_never_taken_or_modified` |
| Rutas relativas y absolutas | `realpath` las une | `test_relative_and_absolute_paths_to_the_same_file_are_one_name` |
| Concurrencia (dos workers, mismo nombre) | `O_EXCL`: uno gana; el otro falla sin tocar el archivo; el archivo es el del ganador (duración distinta) | `test_two_jobs_racing_for_one_name_leave_one_intact_file` |
| Nombres recortados y plantillas sin `%(id)s` | Colisión detectada antes de descargar | Pruebas de la MediaSource y de extremo a extremo |
| Mayúsculas, separadores, rutas largas, archivos abiertos (Windows) | `normcase` y hash de longitud fija | Pruebas `windows` ⏳ |
| Unicode NFC/NFD | Nombres distintos (como en NTFS y ext4) | `test_names_that_differ_only_in_unicode_normalisation_are_different` |

## 6. Contrato de `JobCompleted` (§8)

- **Productores:** `YtDlpMediaSource.download` publica `JobCompleted(ruta)` solo tras comprobar que el archivo está fuera de la carpeta de parciales y con contenido; la expansión publica `JobCompleted(None)`.
- **Consumidores:** `JobEventApplier` (ahora con el contrato), `JobPresenter` (`completed` con o sin ruta) y `RunQueue` (fin del job).
- **Dobles:** el único uso de `JobCompleted(output_path=None)` para una descarga (`test_same_media_is_downloaded_once_as_video_and_once_as_audio`) daba a video y audio la misma ruta en realidad distinta; ahora cada uno tiene la suya y la prueba comprueba ambas. Los demás usos de `None` son de expansiones. Ninguna prueba se debilitó.

## 7. Migraciones (§9)

Base nueva; actualización desde las versiones 1 y 2 con conservación exacta de filas, enlaces padre-hijo, job requests e índices; `foreign_key_check` vacío; migración fallida deshecha (versión, tablas y datos sin cambios, conexión cerrada); archivo que no es SQLite intacto; compatibilidad con `purge` (ids no reutilizados, `ON DELETE CASCADE` de las job requests) y con `retry` (peticiones conservadas en la migración 3). Todo sobre bases de datos temporales de prueba.

## 8. D1: terminación del árbol de procesos (§10)

| Punto | Revisión |
|---|---|
| Asociación antes de cualquier job | `_start_worker` registra el worker en su terminador antes de devolverlo; ningún job le llega antes. En POSIX, el worker crea su grupo como primera instrucción (`become_process_tree_root`) |
| Carreras | POSIX: si se termina antes de que el worker cree su grupo, se usa `pidfd` sobre el worker (aún sin hijos). Windows: el worker no lanza procesos antes de recibir un job |
| Ciclo de vida del handle | `release()` en el apagado ordenado, el inmediato, el reciclado y la sustitución por caída; handle no heredable (prueba `windows` ⏳) |
| Fallo del worker o del supervisor | Worker caído: se termina su árbol antes de sustituirlo (T35). Supervisor muerto: `KILL_ON_JOB_CLOSE` (Windows, ⏳); en POSIX el grupo queda sin dueño (diferencia documentada en ADR-0029) |
| Terminación pedida | `terminate_tree` y espera; si falla, se registra y se mata el worker |
| Archivos preservados | Terminar no borra la carpeta de parciales ni la reclamación; un `retry` reanuda |
| Interacción con la cancelación y `Ctrl+C` | Terminación forzada tras `cancellation_grace_seconds`; mensajes tardíos ignorados; T49: ningún `Ctrl+C` interrumpe el apagado |
| Riesgo residual | En Windows, un worker que muere mientras arranca puede hacer fallar su registro en el Job Object (`ProcessTreeTerminationError`, que hoy detiene `run`); en POSIX el registro no falla. No se puede comprobar aquí y se observará en la campaña. Sin evidencia de Windows, D1 sigue *aceptada, validación pendiente* |

## 9. Requisitos no funcionales, riesgos y pruebas (§11, §12, §14)

- **Requisitos no funcionales:** cada uno, con su verificabilidad en Linux y lo que necesita de Windows, en el [plan de E2, §8.1](iteration-plan-e2.md#81-trazabilidad-por-requisito-no-funcional). SUP-P04 sigue **pendiente** (se fija en la campaña, paso 13).
- **Riesgos:** lista revisada (versión 1.2). Los riesgos que dependen de Windows (R-02, R-04, R-05, R-06, R-10, R-14, R-17) siguen abiertos o *Mitigado (Linux)*; ninguno se cerró con evidencia de Linux. Nuevos: R-15 a R-18.
- **Pruebas:** clasificación en el [plan de E2, §8.2](iteration-plan-e2.md#82-clasificación-de-las-pruebas-2026-11-26-main-tras-la-actualización-de-yt-dlp). Las 3 pruebas `network` se ejecutaron una vez: fallan por el proxy del entorno (`403 Forbidden` al conectar con YouTube), no por el producto; quedan como *no ejecutables aquí*.

## 10. Proceso RUP (§15) y preparación de T42 (§16)

- **Caso de desarrollo:** ajuste por la entrada de UC-07 a UC-10 en E2; tabla de los cinco estados del producto (implementación, verificación de desarrollo, validación en la plataforma, evaluación de la iteración, aceptación final); comprobaciones con `run_checks.py`; evidencia de E1 conservada sin presentarla como validación de la build actual.
- **Guion de la campaña:** versión 2.0, con el commit evaluado por etiqueta (`t42-candidate-1`), entorno aislado en `C:\qmd-t42` (nunca la cola ni las descargas reales), automatización en `scripts/windows/t42_campaign.ps1` (no ejecutado en Linux; su primera ejecución es parte de la campaña), criterios de aceptación, pasos obligatorios, clasificación de defectos y procedimiento de corrección y regresión.

## 11. Pendiente para la campaña

Las 10 pruebas `windows`, las 3 `network`, los pasos 1 a 13 del guion (obligatorios 3, 6, 7, 8 y 11), la medición de memoria y SUP-P04. Hasta entonces: `WINDOWS_VALIDATION_PENDING` y `FINAL_ACCEPTANCE_PENDING`.
