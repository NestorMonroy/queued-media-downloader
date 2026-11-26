# UC-12: Esperar a que vuelva la red

- **Actor principal:** User
- **Actor secundario:** Media site
- **Significativo para la arquitectura:** sí (job event `JobDeferred`, planificación de `run`, comprobación de la conexión en el proceso principal)
- **Estado:** propuesto
- **Decisiones relacionadas:** [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md) (propuesta), [ADR-0008](../../notes/adr-0008-process-based-worker-pool.md)

## Breve descripción

Si el equipo pierde la conexión mientras `run` trabaja, el sistema no marca los jobs `FAILED` uno tras otro. Devuelve a la cola los jobs afectados sin gastar un intento, deja de enviar jobs, comprueba la conexión cada cierto tiempo y continúa cuando vuelve. Un fallo de red aislado, con la conexión funcionando, se reintenta solo unas pocas veces antes de fallar.

## Precondiciones

- `run` está en ejecución.

## Flujo básico

1. Un worker falla con un error de red que indica falta de conexión: no se resuelve el nombre del sitio, la conexión es rechazada o la red no es alcanzable.
2. El worker publica `JobDeferred` con el motivo **sin conexión**, el host y el mensaje.
3. El sistema devuelve el job a `PENDING`, sin incrementar `attempt_count` y conservando sus archivos parciales. Deja de enviar jobs y avisa en inglés: `No network connection; waiting for it to come back (checking every 30 s)`.
4. Los jobs que siguen en curso terminan o fallan. Los que fallen por la misma causa también vuelven a `PENDING`.
5. Cada `network_check_seconds`, el sistema comprueba la conexión desde el proceso principal: resuelve el nombre del último host que falló y abre una conexión TCP al puerto 443, sin descargar nada.
6. La comprobación tiene éxito: el sistema avisa (`Network connection is back; continuing`) y vuelve a enviar jobs. Las descargas continúan desde sus archivos parciales (UC-06).

## Flujos alternativos

- **A1. Fallo de red aislado** (paso 1): un timeout o una conexión cortada con un host concreto, mientras la comprobación del paso 5 tiene éxito. El sistema reintenta el mismo job tras `network_retry_delay_seconds` y luego el doble, hasta `network_retry_attempts` veces, sin gastar intentos de `retry`. Si sigue fallando, el job pasa a `FAILED` con `NETWORK`, como hasta ahora (UC-03 A2).
- **A2. Varios fallos de red seguidos de jobs distintos** (paso 1): aunque el error no indique falta de conexión (por ejemplo, timeouts), dos jobs seguidos con `NETWORK` en menos de `network_check_seconds` se tratan como un corte: el sistema comprueba la conexión (paso 5) antes de enviar otro.
- **A3. La red no vuelve:** `run` sigue esperando y repite el aviso cada `network_notice_minutes`. Un `Ctrl+C` lo detiene con código `130`; los jobs siguen `PENDING` y el siguiente `run` comprueba la conexión antes de enviar jobs.
- **A4. Corte durante una expansión** (UC-04 A6): la expansión vuelve a `PENDING`, sus hijos ya creados se conservan, y al continuar encuentra sus entradas ya creadas como duplicadas (UC-04 A2).
- **A5. El host del sitio está caído, pero el resto de la red funciona:** la comprobación del paso 5 apunta a ese host, así que sigue fallando y el sistema sigue esperando; los jobs de otros sitios no se envían durante la espera. Esta versión no separa la espera por sitio en los cortes de red.
- **A6. `run` se cierra durante la espera:** no se guarda nada; el siguiente `run` comprueba la conexión antes de enviar el primer job y, si no hay, empieza en el paso 3.
- **A7. El User cancela un job que espera** (UC-05 A1): es `PENDING`, así que pasa a `CANCELLED`.

## Excepciones

- **E1. Error de red no reconocido como falta de conexión** (un `HTTP 5xx`, por ejemplo): se trata como A1.
- **E2. Configuración no válida:** error de configuración con la clave y el valor, código `2`, antes de enviar ningún job.

## Postcondiciones

- **Éxito:** ningún job quedó `FAILED` por el corte; la cola continuó sola al volver la red, desde lo ya descargado.
- **Fallo aislado (A1):** el job `FAILED` con `NETWORK` tras sus reintentos automáticos; el resto de la cola continúa (SUP-R03).

## Transiciones

`RUNNING → PENDING` por `JobDeferred` (pasos 2 y 3, A4), sin incrementar `attempt_count`. `RUNNING → FAILED` solo tras agotar los reintentos automáticos de A1.

## Requisitos especiales

- La comprobación de la conexión no descarga contenido ni hace peticiones HTTP al sitio, para no sumar peticiones a su límite (UC-11).
- La espera no aumenta la memoria ni deja workers ocupados: los workers esperan instrucciones como con la cola vacía.

## Configuración

| Clave | Por defecto | Significado |
|---|---|---|
| `network_check_seconds` | 30 | Cada cuánto se comprueba la conexión durante una espera; también la ventana de A2 |
| `network_notice_minutes` | 5 | Cada cuánto se repite el aviso mientras se espera |
| `network_retry_attempts` | 2 | Reintentos automáticos de un fallo aislado (A1) |
| `network_retry_delay_seconds` | 10 | Pausa antes del primer reintento automático; el siguiente espera el doble |

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Clasificación: falta de conexión (resolución de nombres, rechazo, red inalcanzable) frente a fallo aislado, con excepciones reales de yt-dlp | Cualquier sistema |
| `JobDeferred` y espera; continuación al volver la red; A2 con dos fallos seguidos | Cualquier sistema (`ScriptedWorkerPool`, comprobador de conexión falso, reloj falso) |
| Reintento automático y `FAILED` al agotarlo (A1) | Cualquier sistema |
| Corte real contra el servidor local (se detiene el servidor a mitad de una descarga y se vuelve a arrancar) | Cualquier sistema |
| Corte real del equipo (desconectar la red a mitad de una cola) | **Windows**, campaña |
