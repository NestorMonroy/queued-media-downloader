# UC-12: Esperar a que vuelva la red

- **Objetivo:** si el equipo pierde la conexión, la cola no se pierde: los contenidos esperan y la descarga continúa sola, desde lo ya descargado, cuando vuelve la red.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** suceso externo durante `run`: un job falla porque el equipo no tiene conexión (regla [BR-05](../business-rules.md)).
- **Relación:** extiende UC-03 (pasos 4 a 10) y UC-04 (paso 2).
- **Prioridad:** alta
- **Significativo para la arquitectura:** sí
- **Estado:** propuesto
- **Diseño propuesto:** [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md)

## Breve descripción

Si el equipo pierde la conexión, `run` no marca los jobs como fallidos uno tras otro. Deja los afectados en la cola, deja de enviar jobs, comprueba la conexión cada cierto tiempo y continúa cuando vuelve. Un fallo de red aislado, con la conexión funcionando, se reintenta solo unas pocas veces antes de fallar.

## Precondiciones

- `run` está en ejecución.

## Flujo básico

1. Un job falla porque el equipo no tiene conexión ([BR-05](../business-rules.md)).
2. El sistema aplaza el job ([BR-04](../business-rules.md)), deja de enviar jobs y avisa al User: `No network connection; waiting for it to come back (checking every 30 s)` ([BR-11](../business-rules.md)).
3. Los jobs en curso terminan; los que fallan por la misma causa también se aplazan.
4. El sistema comprueba la conexión cada cierto tiempo ([BR-06](../business-rules.md)).
5. Vuelve la conexión: el sistema avisa (`Network connection is back; continuing`) y vuelve a enviar jobs. Las descargas aplazadas continúan desde lo ya descargado (UC-06).

## Flujos alternativos

- **A1. Fallo de red aislado** (paso 1): hay conexión, pero falla un host concreto (un timeout, una conexión cortada, un `HTTP 5xx`). El sistema reintenta el job ([BR-07](../business-rules.md)); si sigue fallando, el job falla con `NETWORK` como en UC-03 A2 y el resto de la cola continúa.
- **A2. La red no vuelve** (paso 4): `run` sigue esperando y repite el aviso ([BR-11](../business-rules.md)). Si el User pulsa `Ctrl+C`, `run` termina con código `130` y los jobs siguen pendientes.
- **A3. El corte llega durante la expansión de una playlist** (UC-04): la expansión se aplaza; las entradas ya creadas se conservan, y al continuar la expansión las encuentra como duplicadas (UC-04 A2).
- **A4. `run` arranca sin conexión** (UC-06 A10): el sistema comprueba la conexión antes de enviar el primer job y, si no hay, empieza en el paso 2.
- **A5. El equipo despierta de una suspensión:** la conexión puede tardar unos segundos en volver; es el flujo básico.
- **A6. El User cancela un job que espera:** como UC-05 A1.

## Excepciones

- **E1. Configuración no válida:** `run` informa de la clave y del valor y termina con código `2` sin enviar jobs.

## Garantías

- **De éxito:** ningún job quedó fallido por el corte; la cola continuó sola al volver la red, desde lo ya descargado.
- **Mínima** (también si `run` termina): ningún job quedó fallido por el corte; los archivos parciales se conservan.

## Requisitos especiales

- SUP-R06 y SUP-U04 ([especificación complementaria](../supplementary-specification.md)).
- La comprobación de la conexión no hace peticiones HTTP al sitio, para no sumar peticiones a su límite (UC-11).

## Configuración

`network_check_seconds` ([BR-05](../business-rules.md), [BR-06](../business-rules.md)); `network_retry_attempts` y `network_retry_delay_seconds` ([BR-07](../business-rules.md)); `network_notice_minutes` ([BR-11](../business-rules.md)).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| BR-05 con excepciones reales de yt-dlp: falta de conexión frente a fallo aislado | Cualquier sistema |
| Pasos 1 a 5, A2 y A4 con un pool guionizado, un comprobador de conexión falso y un reloj falso | Cualquier sistema |
| A1: reintento automático y fallo al agotarlo | Cualquier sistema |
| Corte real contra el servidor local: se detiene a mitad de una descarga y se vuelve a arrancar | Cualquier sistema |
| Corte real del equipo (desconectar la red a mitad de una cola) | **Windows**, campaña (VUC-04) |
