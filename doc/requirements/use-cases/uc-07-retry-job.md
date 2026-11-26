# UC-07: Reintentar un job

- **Objetivo:** los jobs fallidos o cancelados vuelven a la cola y continúan desde lo ya descargado.
- **Actor principal:** User
- **Disparador:** el User ve jobs `FAILED` o `CANCELLED` que quiere volver a intentar.
- **Significativo para la arquitectura:** no (reutiliza las job requests de UC-05 y la reanudación de UC-06)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: los escenarios originales están implementados; los ampliados tienen la marca de su flujo (`[estado: …]`).
- **Verificación:** escenarios implementados verificados con pruebas automáticas en desarrollo (Linux); validación en Windows pendiente de la campaña integral (T42 parcial, [registro](../../project-management/t42-results.md)).
- **Decisiones relacionadas:** [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md), [ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)
- **Diseño:** [Parte 2, §2.4 y §4.1](../../design/02-flows-persistence-and-operations.md#41-comandos)

## Breve descripción

El User vuelve a poner en la cola jobs que fallaron o que canceló. Como `cancel`, `retry` solo registra job requests; el proceso de `run` las aplica.

## Precondiciones

- Existen los jobs indicados.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader retry JOB_ID...`.
2. El sistema registra, en una sola transacción, una job request `RETRY` por cada job `FAILED` o `CANCELLED` (una sola por job aunque se repita el id), informa de cada una y termina con código `0`.
3. El proceso de `run` lee las job requests pendientes (al arrancar o en su siguiente ciclo).
4. El job vuelve a `PENDING`, incrementa `attempt_count` y borra su failure reason y su mensaje. Conserva `selected_format_id` y su carpeta de parciales, para reanudar (UC-06).
5. El sistema marca la job request como procesada; el job se ejecuta como en UC-03 o UC-04.

## Flujos alternativos

- **A1. `--all-failed`** `[estado: implementado]` (paso 1): se registran los reintentos de todos los jobs `FAILED`; los `CANCELLED` no se incluyen. Sin jobs `FAILED`, el sistema informa `No failed jobs to retry` y termina con código `0`.
- **A2. Job no reintentable** `[estado: implementado]` (paso 2): `PENDING`, `RUNNING`, `CANCELLATION_REQUESTED`, `COMPLETED` o `SKIPPED`. El sistema lo informa (`Job N is STATUS; only FAILED or CANCELLED`) y registra los demás.
- **A3. Reintentar una playlist** `[estado: implementado]` (paso 4): vuelven a `PENDING` la expansión y sus descendientes `FAILED` o `CANCELLED`, cada uno con un intento más. Los `COMPLETED` no cambian y no se vuelven a descargar. La nueva expansión encuentra las entradas ya existentes como duplicadas y las crea como hijos `SKIPPED` (UC-04 A2), así que ningún contenido se descarga dos veces.
- **A4. El job dejó de ser reintentable antes de procesarse** `[estado: implementado]` (paso 4): por ejemplo, ya se reintentó con otra job request. La job request se marca procesada sin cambios; no se suma otro intento (idempotencia).
- **A5. `run` no está en ejecución** `[estado: implementado]` (paso 3): la job request se procesa al arrancar el siguiente `run`.
- **A6. El formato guardado ya no está disponible** `[estado: implementado]` (paso 5): como UC-06 A1.
- **A7. Otro job ya es dueño del nombre final** `[estado: implementado]` (paso 5): el job vuelve a fallar con `FILESYSTEM` sin tocar el archivo ajeno ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)).
- **A8. Job con resultados parciales** `[estado: ausente]` (paso 5; D-15): al reintentar, solo se producen los resultados obligatorios que faltan o que no superan la verificación; los completos y propios se conservan.

## Excepciones

- **E1. Sin ids ni `--all-failed`:** `[estado: implementado]` error de uso, código `2`.
- **E2. Job inexistente** `[estado: implementado]` (paso 2): no se registra ninguna job request de esa invocación; código `2`.
- **E3. Base de datos ocupada más allá de `busy_timeout`** `[estado: implementado]` (paso 2): `the queue is busy`, nada se registra, código `1`.

## Postcondiciones

- **Éxito:** una job request `RETRY` por job reintentable; tras procesarla, el job está `PENDING` con un intento más.
- **Fallo (E1–E3):** ningún cambio en la cola.

## Transiciones

`FAILED → PENDING` y `CANCELLED → PENDING`, con `attempt_count + 1`. Ninguna otra.

## Contrato del comando

| Entrada | Efecto | Código |
|---|---|---|
| `retry ID...` | `RETRY` por cada job `FAILED` o `CANCELLED`; informa de los demás | `0` |
| `retry --all-failed` | `RETRY` por cada job `FAILED` | `0` |
| Sin argumentos / id inexistente | Nada se registra | `2` |
| Base de datos ocupada | Nada se registra | `1` |

## Requisitos especiales

- `retry` solo crea job requests; nunca cambia estados ([Parte 2, §2.4](../../design/02-flows-persistence-and-operations.md#24-escritura-desde-varios-procesos)).
- Reintentar nunca descarga de nuevo un contenido `COMPLETED` ni crea descargas duplicadas.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-14, BR-15, BR-17, BR-21.
- **Requisitos suplementarios:** SUP-C04, SUP-U05 (sin implementar).
- **Restricciones:** `retry` solo registra una job request; la aplica el proceso de `run`.
- **Dependencias:** UC-03, UC-06.

## Criterios de aceptación

1. Un job `FAILED` o `CANCELLED` reintentado vuelve a `PENDING` con `attempt_count` incrementado.
2. La descarga continúa desde sus parciales.
3. Un job no reintentable no cambia (A2).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Registro de reintentos, no reintentables e id inexistente | Cualquier sistema |
| `--all-failed` | Cualquier sistema |
| `run` aplica `RETRY`: nuevo intento que termina `COMPLETED` | Cualquier sistema |
| A3 e idempotencia: peticiones repetidas, entrada `COMPLETED` intacta, cada entrada descargada una vez | Cualquier sistema |
| E3 con un bloqueo real de otra conexión | Cualquier sistema |
| Reintento de extremo a extremo en Windows | **Windows**, campaña (paso 5) |
