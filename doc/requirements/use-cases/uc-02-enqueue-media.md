# UC-02: Encolar contenido

- **Objetivo:** los contenidos que interesan al User quedan en la cola, con sus opciones, para descargarse después.
- **Actor principal:** User
- **Disparador:** el User encuentra contenidos que quiere descargar.
- **Significativo para la arquitectura:** sí
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: los escenarios originales están implementados; los ampliados tienen la marca de su flujo (`[estado: …]`).
- **Verificación:** escenarios implementados verificados con pruebas automáticas en desarrollo (Linux); validación en Windows pendiente de la campaña integral (T42 parcial, [registro](../../project-management/t42-results.md)).
- **Decisiones relacionadas:** [ADR-0009](../../notes/adr-0009-playlist-expansion-into-jobs.md), [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md)
- **Diseño:** [Parte 2, §1.1](../../design/02-flows-persistence-and-operations.md#11-encolar)

## Breve descripción

El User añade una o varias URLs a la cola, con sus download options. El sistema crea un job de expansión por URL, sin extraer ni descargar nada.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader enqueue URL... [--format SELECTOR] [--audio-only] [--playlist] [--download-directory DIR]`.
2. El sistema construye las download options combinando los argumentos con la configuración (argumentos > variables de entorno > `config.toml` > valores por defecto).
3. El sistema valida cada URL (forma de URL) y las download options.
4. Para cada URL, el sistema crea un job `EXPANSION` en estado `PENDING` con sus download options fijadas.
5. El sistema muestra el id de cada job creado (por ejemplo, `Queued job 42`) y termina con código `0`.

## Flujos alternativos

- **A1. URL no válida** `[estado: implementado]` (paso 3): el sistema indica cuál es, no crea ningún job de esa invocación y termina con código `2`.
- **A2. `run` en ejecución en otra terminal** `[estado: implementado]` (paso 4): la creación funciona igual (SQLite en modo WAL); el proceso de `run` toma el job en su siguiente ciclo.
- **A3. Base de datos bloqueada más allá de `busy_timeout`** `[estado: implementado]` (paso 4): el sistema informa del bloqueo y termina con código `1` sin crear jobs (los jobs de una invocación se crean en una sola transacción).
- **A4. La base de datos no se puede abrir o una migración falla** `[estado: implementado]` (paso 4): como UC-01 A8; ningún job se crea.
- **A5. URLs de un archivo** `[estado: ausente]` (paso 1; prioridad baja, [análisis](../requirements-analysis.md) §4.1): `enqueue --from-file FILE` lee una URL por línea, sin líneas vacías ni comentarios `#`. Si alguna línea no es una URL válida, es A1: el sistema indica la línea y no encola ninguna.
- **A6. Seleccionar entradas de una playlist** `[estado: ausente]` (paso 1; prioridad media): `--playlist-items 1-5,8` guarda la selección en las download options; la expansión solo crea esas entradas (UC-04 A8). Origen: la selección de entradas de Seal y la opción `--playlist-items` de yt-dlp. La consulta previa (UC-15) muestra las entradas.
- **A7. Información complementaria junto con el contenido** `[estado: ausente]` (paso 1): `--subtitles IDIOMAS`, `--auto-subtitles`, `--embed-subtitles`, `--thumbnail`, `--embed-thumbnail`, `--description`, `--metadata`, `--info-json`. Cada una se guarda en las download options; al descargar, son resultados complementarios del job (UC-03 A16), obligatorios u opcionales según [BR-29](../business-rules.md). Para obtener solo la información, sin el contenido: UC-24.
- **A8. Rango de tiempo** `[estado: ausente]` (paso 1; prioridad baja): `--section 00:01:00-00:02:30` descarga solo ese tramo, con `download_ranges` de yt-dlp. Origen: los recortes de Seal y la opción `--download-sections` de Kannagi y yt-dlp.
- **A9. Calidad por preajuste** `[estado: ausente]` (paso 1; prioridad media): `--quality 1080p` (también `720p`, `480p`, `360p` o `best`) se traduce a un format selector que limita la altura del video y une el mejor audio, sin que el User escriba la sintaxis de yt-dlp. `--format` sigue disponible y tiene prioridad. Origen: los preajustes de calidad de YTDownload-2026, Seal y Kannagi.
- **A10. Segmentos de SponsorBlock** `[estado: ausente]` (paso 1; decisión D-18): `--sponsorblock-mark CATEGORÍAS` marca los segmentos como capítulos; `--sponsorblock-remove CATEGORÍAS` los quita del resultado. La petición forma parte de la identidad de la variante (BR-32): quitar segmentos produce un resultado distinto del original. Origen: Seal; postprocessors `SponsorBlock` y `ModifyChapters` de yt-dlp.
- **A11. Capítulos** `[estado: ausente]` (paso 1; decisión D-18): `--split-chapters` produce un archivo por capítulo además del completo, o en su lugar; `--chapters PATRÓN` descarga solo los capítulos cuyo título coincide (`download_ranges` de yt-dlp). Útil para cursos, conferencias, podcasts y audiolibros. Cambia el número de resultados del job (D-15).
- **A12. Acceso autorizado** `[estado: ausente]` (paso 1; D-1 y D-7): `--access NOMBRE` indica un perfil de acceso (UC-19). El job guarda el nombre del perfil, nunca credenciales ([BR-34](../business-rules.md)).
- **A13. Perfil de descarga** `[estado: ausente]` (paso 1): `--profile NOMBRE` copia las opciones del perfil en el job (UC-18, [BR-33](../business-rules.md)).
- **A14. Contenedor y conversión** `[estado: ausente; condicionado]` (paso 1; decisión D-18): `--container mkv|mp4` cambia el contenedor sin recodificar (remux); `--audio-format mp3|m4a|opus` convierte el audio; `--recode CÓDEC` recodifica el video solo con un codificador disponible en la build incluida ([análisis, §13.4](../requirements-analysis.md#134-recodificación-y-compatibilidad)). Una combinación imposible es E1 de UC-18.

## Postcondiciones

- **Éxito:** un job `EXPANSION` `PENDING` por URL. Si después cambia la configuración, esos jobs conservan sus download options.

## Requisitos especiales

- `enqueue` no accede a la red: responde de inmediato aunque la conexión sea lenta.
- `enqueue` solo crea jobs; nunca cambia el estado de jobs existentes ([Parte 2, §2.4](../../design/02-flows-persistence-and-operations.md#24-escritura-desde-varios-procesos)).

## Reglas, requisitos y restricciones asociados

- **Reglas:** ninguna al encolar: los duplicados se detectan al descargar (BR-13 y BR-32). Las opciones aún sin implementar usan BR-29, BR-32, BR-33 y BR-34.
- **Requisitos suplementarios:** SUP-F02, SUP-F03, SUP-C04.
- **Restricciones:** `enqueue` no accede a la red ni cambia jobs existentes.
- **Dependencias:** UC-01; UC-15 orienta sus opciones.

## Criterios de aceptación

1. Cada URL válida produce un job `EXPANSION` `PENDING` con las download options vigentes en ese momento.
2. Una URL no válida no crea ningún job de la invocación (código `2`).
3. `enqueue` responde sin acceder a la red.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Combinación de argumentos y configuración | Cualquier sistema |
| URL no válida: no se crea ningún job | Cualquier sistema |
| Varias URLs en una invocación | Cualquier sistema |
| `enqueue` mientras otro proceso escribe en la base de datos | Cualquier sistema |
