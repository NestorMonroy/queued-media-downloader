# ADR-0031: Aplazar jobs y esperar al sitio, a la red y al disco, sin PO Tokens ni cuentas

- **Estado:** Propuesta (pendiente de las decisiones D-1 a D-4 del Responsable)
- **Fecha:** 2026-11-26
- **Origen:** campaña T42 (corte de red del paso 5.2, bloqueo antibots de YouTube desde el paso 5.7); [análisis](../requirements/unattended-operation-analysis.md)
- **Casos de uso:** [UC-11](../requirements/use-cases/uc-11-wait-out-a-site-block.md), [UC-12](../requirements/use-cases/uc-12-wait-for-the-network.md), [UC-13](../requirements/use-cases/uc-13-wait-for-disk-space.md), [UC-14](../requirements/use-cases/uc-14-pause-and-continue-the-queue.md)
- **Reglas:** BR-01 a BR-12 del [catálogo](../requirements/business-rules.md)

## Contexto

`run` envía el siguiente job en cuanto termina el anterior, y trata cada error como un fallo del job. Cuando YouTube bloquea la sesión o el equipo pierde la red, todos los jobs pendientes quedan `FAILED` en minutos y gastan un intento. Mientras tanto, las peticiones siguen llegando al sitio que bloquea, y el User tiene que notar los fallos, esperar y reintentar a mano (análisis, §4).

yt-dlp 2026.11.23 no tiene una excepción propia para el bloqueo: lo lanza como `ExtractorError` esperado con el texto del sitio (`raise_no_formats`). Sus clientes de YouTube por defecto (`tv_samsung`, `visionos`) no exigen PO Token, y el Responsable decidió no depender de PO Tokens.

## Decisión

1. **Bloqueo del sitio:** se reconoce por el texto de yt-dlp, en `media_extraction` y con una prueba de contrato contra el código real, como `FORMAT_UNAVAILABLE_MESSAGE` y `DOWNLOAD_RETRIES_EXHAUSTED_MESSAGE`. **Falta de conexión:** se reconoce por la causa de red (resolución de nombres, rechazo, red inalcanzable). En los dos casos el worker publica un job event nuevo, **`JobDeferred(defer_reason, site_key, host, message)`**, en lugar de `JobFailed`.
2. **`JobDeferred` devuelve el job a `PENDING`** (`RUNNING → PENDING`) sin incrementar `attempt_count` y sin tocar sus parciales ni su reclamación de nombre.
3. **Sitio de un job (`site_key`):** se fija al encolar, sin red. `media_extraction` busca el extractor de yt-dlp que acepta la URL (sus métodos `suitable`, los mismos que usa yt-dlp para elegir) y, si no hay ninguno, usa el host de la URL. Se guarda en la tabla `jobs`.
4. **Esperas por sitio persistentes:** tabla nueva `site_waits(site_key, defer_reason, waiting_until, consecutive_waits)`, migración 0005, que solo escribe el proceso de `run`. **Esperas de red en memoria:** no se guardan, porque la conexión se comprueba al arrancar.
5. **La planificación es del proceso de `run`.** Al elegir el siguiente job (`get_next_pending`), `RunQueue` salta los sitios con espera vigente y aplica el ritmo por sitio: pausa aleatoria entre el mínimo y el máximo configurados desde el último envío a ese sitio. El worker no duerme: un `sleep` dentro de yt-dlp (`sleep_interval`) no ve la bandera de cancelación, y una pausa mayor que `cancellation_grace_seconds` terminaría en una terminación forzada (UC-05 A2). Solo la pausa corta entre peticiones de una extracción se delega en yt-dlp (`sleep_interval_requests`).
6. **Comprobaciones del entorno** desde el proceso principal, detrás de puertos para probarlas con dobles: `ConnectivityProbe` (BR-06) y `FreeSpaceProbe` (espacio libre de las unidades de descargas y de estado, BR-08 y BR-09). El disco lleno se reconoce por `errno` `ENOSPC` o por `winerror` 112 (`ERROR_DISK_FULL`) o 39 (`ERROR_HANDLE_DISK_FULL`) en la excepción, o por el mensaje de ffmpeg; una prueba de Windows confirma qué valores llegan en cada caso.
7. **Pausa** (UC-14): una job request de cola (`PAUSE`, `RESUME`) en la bandeja existente, aplicada por `run` como las de UC-05; el estado de pausa se guarda en la base de datos.
8. **Sin PO Tokens, cookies ni cuentas** (BR-12, D-1).

## Alternativas descartadas

- **Proveedor de PO Token:** dependencia externa no afiliada a yt-dlp, tokens por video, contraria a la decisión del Responsable e innecesaria con los clientes por defecto.
- **Repetir con `--cookies-from-browser` al ver el error,** como la referencia `yt-dlp-gui-kannagi`: expone la cuenta del User a un bloqueo y depende de leer las cookies del navegador en Windows, que [ADR-0004](adr-0004-windows-x64-target-platform.md) dejó sin verificar.
- **Un motivo de fallo nuevo** (`SITE_BLOCKED`) sin espera: mejora el diagnóstico (O-1), pero los jobs siguen gastándose y el User sigue reintentando a mano.
- **Ritmo con `sleep_interval` de yt-dlp en el worker:** ver el punto 5.

## Consecuencias

- Nuevo job event, nueva transición en el ciclo de vida, columna `site_key` y tabla `site_waits` (migración 0005, aplicable a bases de E1 y E2).
- `RunQueue` gana un reloj inyectable y un `ConnectivityProbe`; sus pruebas siguen sin yt-dlp, sin SQLite y sin procesos (SUP-S04).
- La cola tarda más con YouTube por el ritmo por defecto (D-3), a cambio de menos bloqueos y de no perder la cola cuando ocurren.
- `list` y `show` muestran el motivo y la hora de continuación de un job que espera (UC-08, UC-09).

## Validación

Pruebas de contrato con los textos de yt-dlp; pruebas de `RunQueue` con reloj y comprobador de conexión falsos; un corte real contra el servidor local en cualquier sistema; en Windows, un corte de red real en la campaña. El bloqueo real de YouTube no se provoca a propósito.
