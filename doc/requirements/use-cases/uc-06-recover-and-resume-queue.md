# UC-06: Recuperar la cola y reanudar descargas

- **Objetivo:** la cola continúa tras un cierre inesperado sin perder jobs ni lo ya descargado.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** el User ejecuta `run` después de un cierre inesperado o de un `Ctrl+C`.
- **Significativo para la arquitectura:** sí
- **Decisiones relacionadas:** [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md)
- **Diseño:** [Parte 2, §1.5](../../design/02-flows-persistence-and-operations.md#15-recuperación-y-reanudación)

## Breve descripción

Tras un cierre inesperado (corte de luz, cierre de la terminal, fallo), el User vuelve a ejecutar la cola. El sistema corrige los estados interrumpidos (recuperar) y continúa las descargas parciales desde lo ya descargado (reanudar).

## Precondiciones

- Una ejecución anterior de `run` terminó sin cerrar la cola de forma ordenada.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader run`.
2. El sistema pasa los jobs `RUNNING` a `PENDING` y los `CANCELLATION_REQUESTED` a `CANCELLED`.
3. El sistema procesa las job requests pendientes (por ejemplo, cancelaciones registradas mientras `run` no estaba activo).
4. El sistema envía un job de descarga interrumpido a un worker.
5. El worker pide a yt-dlp el formato `selected_format_id` guardado, con la misma plantilla de salida y `continuedl` activo.
6. yt-dlp vuelve a extraer las URLs de descarga (caducan en horas) y continúa desde el archivo `.part` o el estado `.ytdl`.
7. La descarga termina como en UC-03 (pasos 9 a 11).

## Flujos alternativos

- **A1. El formato guardado ya no está disponible** (paso 6): el worker reintenta una vez con el format selector original y publica `FormatSelected` con el nuevo formato. Al terminar con éxito, se eliminan los `.part` del formato anterior.
- **A2. El job no tenía formato elegido** (paso 5): la interrupción ocurrió antes de `FormatSelected`; la descarga empieza de cero con el format selector original.
- **A3. Archivos parciales borrados por el User** (paso 6): yt-dlp descarga desde el principio.
- **A4. El cierre ocurrió después de mover el archivo final y antes de registrar `JobCompleted`** (paso 6): el job encuentra su propia reclamación y su archivo; yt-dlp lo da por descargado y el job termina `COMPLETED` sin descargar de nuevo ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)).
- **A5. La interrupción fue un `Ctrl+C`** (paso 2): igual que un cierre inesperado; los jobs siguen `RUNNING` con sus parciales (UC-05 A6).
- **A6. La base de datos necesita una migración** (paso 1): se aplica al abrirla; si falla, se deshace y `run` termina con código `1` sin ejecutar ningún job (UC-01 A8).
- **A7. Base de datos de una versión anterior con un archivo final reclamado por dos o más jobs** (paso 1): los datos no permiten saber quién escribió el archivo. La migración 0004 no da la propiedad a ninguno: todos pasan a `FAILED` (reintentables), sin `output_path`, con un mensaje que nombra el archivo, a todos los jobs implicados y su estado conocido. El archivo no se toca; al reintentar, el job falla hasta que el User lo mueva o lo renombre (UC-03 A7).
- **A8. Base de datos restaurada de una copia anterior** (paso 1): los jobs nuevos reciben ids de jobs perdidos. Ninguno hereda lo de esos jobs: su owner token (id e instante de creación) no coincide. Un nombre final reclamado por un job perdido hace fallar al job nuevo sin tocar el archivo; una carpeta de parciales de un job perdido se aparta como `.partial/orphan-job-<id>-<instante>`, sin borrar nada, y la descarga empieza de cero. `purge` suelta las reclamaciones de los jobs perdidos; sus archivos siguen protegidos ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)).
- **A9. Un job `COMPLETED` cuyo archivo final ya no existe** (lo movió o borró el User): la cola no cambia nada; `show` sigue mostrando la ruta guardada. Ningún archivo se crea, se toca ni se borra por ello.
- **A10. Había una espera del sitio** (propuesto, [UC-11](uc-11-wait-out-a-site-block.md) A6): sigue vigente tras el cierre; `run` avisa al arrancar de la hora de continuación. Las esperas de red no se guardan: `run` comprueba la conexión antes del primer job ([UC-12](uc-12-wait-for-the-network.md) A6).

## Postcondiciones

- **Éxito:** ningún job queda en `RUNNING` sin un worker; las descargas interrumpidas continúan sin repetir lo ya descargado.
- **Fallo (A6):** la cola no cambia.

## Transiciones

`RUNNING → PENDING` y `CANCELLATION_REQUESTED → CANCELLED` al recuperar; después, las de UC-03.

## Restricciones

- La reanudación por bytes depende de que el sitio acepte `Range` y de que yt-dlp conserve el `.part`; si no, la descarga empieza de cero (A3).
- Una carpeta de descargas tiene una sola autoridad: una cola (un `state_directory`). Con dos colas sobre la misma carpeta, la propiedad de los archivos finales no se garantiza ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md), restricciones).

## Requisitos especiales

- La plantilla de salida es determinista entre ejecuciones (la construye el proyecto a partir de datos guardados).
- La recuperación se ejecuta antes de enviar ningún job.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Recuperación de estados (paso 2) | Cualquier sistema |
| Plantilla de salida determinista | Cualquier sistema |
| Reanudación real: interrumpir una descarga del servidor HTTP local y continuar | Cualquier sistema |
| Formato no disponible (A1) con `FakeMediaSource` | Cualquier sistema |
| Cierre forzado de `run` en Windows y reanudación | **Windows**, al cerrar la iteración |
| A4: cierre tras mover el archivo; el mismo job lo reconoce como suyo | Cualquier sistema |
| A6 y A7: migración fallida deshecha; base de E1 con un archivo reclamado varias veces, también si ya tenía aplicada la 0003 | Cualquier sistema |
| A8: id reutilizado tras restaurar una copia: reclamación y parciales del job perdido intactos | Cualquier sistema |
