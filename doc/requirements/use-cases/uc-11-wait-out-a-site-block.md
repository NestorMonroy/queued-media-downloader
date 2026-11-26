# UC-11: Esperar a que el sitio levante un bloqueo

- **Objetivo:** los contenidos de un sitio que bloquea se descargan cuando el sitio vuelve a responder, sin que ninguno quede fallido, sin pedirle nada mientras bloquea y sin que el User intervenga.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** suceso externo durante `run`: el Media site responde a una petición con un bloqueo de la sesión (regla [BR-01](../business-rules.md)).
- **Relación:** extiende UC-03 (pasos 4 a 10) y UC-04 (paso 2).
- **Prioridad:** alta
- **Significativo para la arquitectura:** sí
- **Estado:** propuesto; decisiones D-1 a D-4 pendientes ([análisis](../unattended-operation-analysis.md))
- **Diseño propuesto:** [ADR-0031](../../notes/adr-0031-site-waits-and-network-waits.md)

## Breve descripción

`run` pide al Media site a un ritmo que reduce el riesgo de bloqueo. Si el sitio bloquea de todos modos, el contenido afectado vuelve a la cola sin gastar un intento y `run` deja de pedir a ese sitio durante una espera, mientras sigue con los demás sitios. Al terminar la espera, prueba con un solo contenido antes de continuar.

## Precondiciones

- `run` está en ejecución y hay jobs pendientes del sitio.

## Flujo básico

1. El sistema envía el siguiente job del sitio respetando el ritmo de peticiones del sitio ([BR-02](../business-rules.md)).
2. El Media site responde con un bloqueo de la sesión ([BR-01](../business-rules.md)).
3. El sistema aplaza el job ([BR-04](../business-rules.md)).
4. El sistema deja de enviar jobs de ese sitio durante una espera ([BR-03](../business-rules.md)) y avisa al User del sitio, el motivo y la hora de continuación ([BR-11](../business-rules.md)); por ejemplo, `youtube is blocking requests (bot check); waiting until 00:47, other sites continue`.
5. Los jobs de otros sitios siguen descargándose.
6. Al terminar la espera, el sistema envía un solo job del sitio.
7. El Media site responde con normalidad: el sistema avisa de que el sitio vuelve a responder y continúa con los demás jobs del sitio, desde el paso 1.

## Flujos alternativos

- **A1. La prueba vuelve a encontrar el bloqueo** (paso 7): el sistema aplaza el job y espera de nuevo, el doble que la vez anterior hasta el máximo ([BR-03](../business-rules.md)); el aviso indica cuántas esperas seguidas lleva el sitio.
- **A2. Todo lo pendiente espera a sitios bloqueados** (paso 5): `run` sigue esperando y repite el aviso ([BR-11](../business-rules.md)); decisión D-2. Si el User pulsa `Ctrl+C`, `run` termina con código `130`; los jobs siguen pendientes y la espera sigue vigente.
- **A3. Varios jobs del sitio encuentran el bloqueo a la vez** (paso 2): cada uno se aplaza; la espera es una sola.
- **A4. El bloqueo llega durante la expansión de una playlist** (UC-04): la expansión se aplaza; las entradas ya creadas se conservan y esperan con su sitio. Al continuar, la expansión encuentra esas entradas como duplicadas (UC-04 A2).
- **A5. El bloqueo llega a mitad de una descarga:** como el paso 3; al continuar, la descarga sigue desde lo ya descargado (UC-06).
- **A6. `run` termina o se cierra durante la espera:** el siguiente `run` respeta la espera pendiente y avisa al arrancar de la hora de continuación (UC-06 A10).
- **A7. El User quiere probar antes de tiempo:** ejecuta `run --ignore-site-waits`; el sistema empieza por el paso 6.
- **A8. El User cancela un job que espera:** como UC-05 A1 (el job está pendiente).

## Excepciones

- **E1. La respuesta del sitio no se reconoce como bloqueo:** el job sigue UC-03 A2 (falla con su motivo). Si yt-dlp cambia sus textos, la prueba de contrato de BR-01 falla al actualizarlo (SUP-S01).
- **E2. Configuración no válida** (un intervalo negativo, un máximo menor que el mínimo): `run` informa de la clave y del valor y termina con código `2` sin enviar jobs.

## Garantías

- **De éxito:** todos los jobs del sitio se descargan cuando el sitio vuelve a responder; ninguno quedó fallido ni gastó un intento por el bloqueo; el sitio no recibió peticiones durante su espera, salvo la prueba del paso 6.
- **Mínima** (también si `run` termina o se cierra): ningún job quedó fallido por el bloqueo; los archivos parciales y las reclamaciones de nombre se conservan; la espera queda guardada.

## Requisitos especiales

- SUP-R07, SUP-P05 y SUP-U04 ([especificación complementaria](../supplementary-specification.md)).
- Ni PO Tokens, ni cookies, ni cuentas ([BR-12](../business-rules.md)).

## Configuración

`site_request_interval_seconds`, `site_request_max_interval_seconds` y `site_sleep_requests_seconds` ([BR-02](../business-rules.md)); `site_block_wait_minutes` y `site_block_max_wait_minutes` ([BR-03](../business-rules.md)); `site_block_notice_minutes` ([BR-11](../business-rules.md)).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| BR-01 con el código real de yt-dlp: las tres respuestas de bloqueo frente a un contenido que pide una cuenta | Cualquier sistema |
| Pasos 2 a 7, A1 y A3 con un pool guionizado y un reloj falso: aplazamiento sin gastar intento, espera única, espera creciente | Cualquier sistema |
| Ritmo por sitio (BR-02) con dos sitios a la vez | Cualquier sistema |
| A2, A6 y A7: espera guardada tras un cierre, aviso al arrancar, `--ignore-site-waits` | Cualquier sistema |
| Bloqueo real de YouTube | **Windows**, solo si ocurre; no se provoca a propósito |
