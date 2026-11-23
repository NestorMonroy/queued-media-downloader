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
