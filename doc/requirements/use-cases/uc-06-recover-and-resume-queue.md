# UC-06: Recuperar la cola y reanudar descargas

- **Actor principal:** User
- **Actor secundario:** Media site
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

## Postcondiciones

- **Éxito:** ningún job queda en `RUNNING` sin un worker; las descargas interrumpidas continúan sin repetir lo ya descargado.

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
