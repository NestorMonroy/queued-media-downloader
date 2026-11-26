# UC-11: Esperar a que el sitio levante un bloqueo

- **Actor principal:** User
- **Actor secundario:** Media site
- **Significativo para la arquitectura:** sí (nuevo job event, nuevo estado persistente por sitio, planificación de `run`)
- **Estado:** propuesto; pendiente de las decisiones D-1 a D-4 del [análisis](../site-blocks-and-network-outages-analysis.md)
- **Decisiones relacionadas:** [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md) (propuesta), [ADR-0008](../../notes/adr-0008-process-based-worker-pool.md), [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md)

## Breve descripción

`run` pide al Media site a un ritmo que reduce el riesgo de bloqueo. Si el sitio bloquea de todos modos (comprobación antibots, captcha o límite de peticiones), el job afectado vuelve a la cola sin gastar un intento. `run` deja de enviar jobs a ese sitio durante una espera, sigue con los de otros sitios, y al terminar la espera prueba con un solo job antes de continuar. Nunca se usan PO Tokens ni cuentas del sitio.

## Precondiciones

- `run` está en ejecución y hay jobs `PENDING` del sitio.

## Flujo básico

1. El sistema toma el siguiente job `PENDING` de un sitio sin espera vigente, respetando el ritmo del sitio: no lo envía antes de que pase, desde el anterior job de ese sitio, un intervalo aleatorio entre `site_request_interval_seconds` y `site_request_max_interval_seconds` (SUP-P05).
2. El worker extrae el contenido. yt-dlp espera `site_sleep_requests_seconds` entre las peticiones de la extracción.
3. El Media site responde con un bloqueo: `Sign in to confirm you're not a bot`, un captcha o `This content isn't available, try again later`.
4. El worker clasifica la respuesta como **bloqueo del sitio** y publica `JobDeferred`, con el motivo, el sitio y el mensaje del sitio.
5. El sistema devuelve el job a `PENDING`, sin incrementar `attempt_count` y conservando su carpeta de parciales, y guarda una espera para el sitio: `waiting_until` es ahora más `site_block_wait_minutes`. Avisa en inglés con el sitio, el motivo y la hora local de continuación (SUP-U04); por ejemplo, `youtube is blocking requests (bot check); waiting until 00:47, other sites continue`.
6. Mientras dura la espera, el sistema no envía jobs de ese sitio. Los jobs de otros sitios siguen.
7. Al terminar la espera, el sistema envía un solo job del sitio (prueba).
8. La prueba termina sin bloqueo: el sistema borra la espera y continúa con el ritmo del paso 1.

## Flujos alternativos

- **A1. La prueba vuelve a encontrar el bloqueo** (paso 7): el job vuelve a `PENDING`, y la nueva espera dura el doble de la anterior, hasta `site_block_max_wait_minutes`. El aviso indica el número de esperas seguidas.
- **A2. Todos los jobs pendientes esperan a sitios bloqueados** (paso 6): `run` no termina (decisión D-2). Repite el aviso con la hora de continuación cada `site_block_notice_minutes` y sigue esperando. Un `Ctrl+C` lo detiene con código `130`; los jobs siguen `PENDING` y la espera guardada sigue vigente.
- **A3. Varios workers encuentran el bloqueo a la vez** (paso 4): cada job vuelve a `PENDING`; la espera se guarda una sola vez y no se alarga por los avisos simultáneos.
- **A4. El bloqueo llega durante una expansión** (UC-04): la expansión vuelve a `PENDING`; los hijos ya creados se conservan y esperan con su sitio. Al continuar, la expansión encuentra sus entradas ya creadas como duplicadas (UC-04 A2).
- **A5. El bloqueo llega a mitad de una descarga** (por ejemplo, un `HTTP 403` del servidor de video tras empezar): igual que el paso 5; la descarga continúa desde sus archivos parciales al terminar la espera (UC-06).
- **A6. `run` se cierra durante una espera** (UC-06): la espera está guardada; el siguiente `run` la respeta y avisa al arrancar de la hora de continuación.
- **A7. El User cancela un job que espera** (UC-05 A1): es `PENDING`, así que pasa a `CANCELLED`.
- **A8. El User quiere probar antes de tiempo:** `run --ignore-site-waits` borra las esperas guardadas y empieza por la prueba del paso 7.
- **A9. Un sitio pide una cuenta para un contenido concreto** (privado, con restricción de edad, solo para miembros): no es un bloqueo del sitio; el job falla con `UNAVAILABLE` como hasta ahora (UC-03 A2). La diferencia se decide con el texto del sitio (requisitos especiales).

## Excepciones

- **E1. La respuesta del sitio no se reconoce:** se clasifica como hasta ahora (UC-03 A2). Una prueba de contrato contra el código de yt-dlp detecta si una actualización cambia los textos (SUP-S01).
- **E2. Configuración no válida** (intervalo negativo, máximo menor que el mínimo): error de configuración con la clave y el valor, código `2`, antes de enviar ningún job.

## Postcondiciones

- **Éxito:** ningún job quedó `FAILED` ni gastó un intento por el bloqueo; los jobs del sitio continúan cuando el sitio vuelve a responder.
- **Interrupción (A2, A6):** jobs `PENDING` con sus parciales; la espera del sitio guardada en la base de datos.

## Transiciones

`RUNNING → PENDING` por `JobDeferred` (pasos 4 y 5, A4, A5), sin incrementar `attempt_count`. No hay transición a `FAILED` por un bloqueo del sitio.

## Requisitos especiales

- Ni PO Tokens, ni cookies, ni cuentas del sitio (restricción del Responsable; decisión D-1).
- El ritmo lo aplica el proceso de `run` al enviar jobs, no un `sleep` dentro del worker: un worker dormido no ve la bandera de cancelación y una pausa mayor que `cancellation_grace_seconds` acabaría en una terminación forzada (ADR-0031).
- El sitio de un job (`site_key`) se determina al encolarlo, sin red: el extractor de yt-dlp que acepta la URL, o su host si no hay ninguno (ADR-0031). Hoy un job `EXPANSION` no conoce su extractor hasta que se ejecuta.
- Los textos que identifican un bloqueo viven en `media_extraction`, junto a `failure_classifier`, con una prueba de contrato contra el código real de yt-dlp.
- Las esperas se guardan en SQLite; solo el proceso de `run` las escribe (SUP-C04).

## Configuración

| Clave | Por defecto (YouTube) | Por defecto (otros sitios) | Significado |
|---|---|---|---|
| `site_request_interval_seconds` | 10 | 0 | Pausa mínima entre jobs del mismo sitio |
| `site_request_max_interval_seconds` | 20 | 0 | Pausa máxima; la pausa es aleatoria entre las dos |
| `site_sleep_requests_seconds` | 0.75 | 0 | Pausa de yt-dlp entre peticiones de una extracción (`sleep_interval_requests`) |
| `site_block_wait_minutes` | 60 | 60 | Primera espera ante un bloqueo |
| `site_block_max_wait_minutes` | 240 | 240 | Espera máxima tras esperas seguidas |
| `site_block_notice_minutes` | 15 | 15 | Cada cuánto se repite el aviso mientras todo espera (A2) |

Los valores por defecto para YouTube son los del preajuste `-t sleep` de yt-dlp (decisión D-3). Todos se pueden bajar hasta 0.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Clasificación de las tres respuestas de bloqueo frente a contenidos que piden una cuenta (A9), con el código real de yt-dlp | Cualquier sistema |
| `JobDeferred`: `RUNNING → PENDING` sin gastar intento; espera guardada; espera creciente (A1) y avisos simultáneos (A3) | Cualquier sistema (`ScriptedWorkerPool`, reloj falso) |
| Ritmo por sitio al enviar jobs, con dos sitios a la vez | Cualquier sistema (reloj falso) |
| Espera guardada tras un cierre (A6) y `--ignore-site-waits` (A8) | Cualquier sistema |
| Cancelación de un job que espera (A7) | Cualquier sistema |
| Bloqueo real de YouTube | **Windows**, solo si ocurre; no se provoca a propósito |
