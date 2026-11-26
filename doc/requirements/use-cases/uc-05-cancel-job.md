# UC-05: Cancelar un job

- **Objetivo:** un job deja de ejecutarse sin dejar procesos vivos ni perder sus archivos parciales.
- **Actor principal:** User
- **Disparador:** el User decide que ya no quiere un contenido, o que una descarga debe parar.
- **Significativo para la arquitectura:** sí
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: los escenarios originales están implementados; los ampliados tienen la marca de su flujo (`[estado: …]`).
- **Verificación:** escenarios implementados verificados con pruebas automáticas en desarrollo (Linux); validación en Windows pendiente de la campaña integral (T42 parcial, [registro](../../project-management/t42-results.md)).
- **Propuestas pendientes de aprobación (2.5.0):** A10, marcadas como propuestas; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Decisiones relacionadas:** [ADR-0008](../../notes/adr-0008-process-based-worker-pool.md), [ADR-0013](../../notes/adr-0013-process-tree-terminator-abstraction.md)
- **Diseño:** [Parte 2, §1.4](../../design/02-flows-persistence-and-operations.md#14-cancelación)

## Breve descripción

El User cancela uno o varios jobs. Si el job aún no empezó, se cancela de inmediato. Si se está ejecutando, se pide al worker que lo detenga y, si no confirma a tiempo, se termina su process tree.

## Precondiciones

- Existe el job indicado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader cancel JOB_ID...`.
2. El sistema registra una job request `CANCEL` por cada job y termina con código `0`.
3. El proceso de `run` lee las job requests pendientes.
4. El job está `RUNNING`: el sistema lo pasa a `CANCELLATION_REQUESTED` y pide la cancelación al worker.
5. El hilo de cancelación del worker activa la bandera; en el siguiente hook de progreso, yt-dlp detiene la descarga.
6. El worker publica `JobCancelled`; el job pasa a `CANCELLED`.
7. El sistema marca la job request como procesada.

## Flujos alternativos

- **A1. Job `PENDING`** `[estado: implementado]` (paso 4): pasa directamente a `CANCELLED`.
- **A2. Sin confirmación en `cancellation_grace_seconds`** `[estado: implementado]` (paso 5): por ejemplo, durante la extracción o mientras ffmpeg une archivos. El sistema termina el process tree del worker (worker, ffmpeg y deno), marca el job `CANCELLED` y arranca un worker de reemplazo.
- **A3. El job termina antes de ver la bandera** `[estado: implementado]` (paso 5): llega `JobCompleted` y el job queda `COMPLETED`.
- **A4. Cancelar una playlist** `[estado: implementado]` (paso 2): se registra `CANCEL` para la expansión y para cada hijo no terminado. La expansión termina (`COMPLETED`) en cuanto crea sus entradas, normalmente en segundos: si ya terminó, se registra `CANCEL` solo para sus descendientes no terminados, la expansión sigue `COMPLETED` y `cancel` informa de cuántas entradas se cancelan. Si no queda ninguna, es A7.
- **A5. `run` no está en ejecución** `[estado: implementado]` (paso 3): la job request se procesa al arrancar el siguiente `run`.
- **A6. `Ctrl+C` durante `run` (interrupción, no cancelación):** `[estado: implementado]` el sistema deja de enviar jobs y detiene los jobs en curso con el mismo mecanismo que la cancelación (pasos 5 y A2), pero **sin cancelarlos**: siguen `RUNNING`, con sus archivos parciales, y no se registra ninguna job request. Un segundo `Ctrl+C` termina el árbol de cada worker de inmediato; los siguientes se ignoran hasta que `run` sale. `run` termina con código `130`, y los jobs interrumpidos se recuperan y se reanudan en el siguiente `run` (UC-06; interrupción recuperable, [ADR-0029](../../notes/adr-0029-process-tree-termination-on-windows.md)).
- **A7. Job ya terminado** `[estado: implementado]` (`COMPLETED`, `FAILED`, `SKIPPED`, `CANCELLED`): no se registra job request; `cancel` informa al User de que el job ya terminó. Si el job terminó entre el registro y el procesamiento, `run` marca la job request procesada sin cambios. Un job `FAILED` conserva su failure reason: no se cancela, se reintenta (UC-07). Ver la tabla de estados terminados, reintentables y cancelables del [vocabulario, §1.1](../../design/00-vocabulary.md#11-estados-terminados-reintentables-y-cancelables).
- **A8. Job `CANCELLATION_REQUESTED`** `[estado: implementado]` (paso 4): ya se está cancelando; la job request se marca procesada sin cambios.
- **A9. Cancelar durante el postprocesamiento con varios resultados** `[estado: ausente]` (paso 5; D-15): los resultados ya publicados en su ruta final se conservan con su reclamación y quedan registrados como parciales del job cancelado; los que no llegaron a publicarse se descartan como parciales. Nunca queda un archivo final a medio escribir: la publicación de cada resultado es un movimiento atómico.
- **A10. Cancelar varios jobs seleccionados** `[estado: ausente; propuesto]` (paso 1): el User cancela una selección de jobs. Cada uno se cancela como en el flujo básico y el resultado se informa por job (cancelado, ya terminado o inexistente); un fallo en uno no impide cancelar los demás. Evidencia: YTDLnis (selección múltiple) y Open Video Downloader (`group_cancel`); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).

## Excepciones

- **E1. Job inexistente** `[estado: implementado]` (paso 2): `cancel` indica qué id no existe, no registra ninguna job request de esa invocación y termina con código `2`.
- **E2. Base de datos bloqueada más allá de `busy_timeout`** `[estado: implementado]` (paso 2): `cancel` informa del bloqueo y termina con código `1` sin registrar nada.
- **E3. La terminación forzada falla** `[estado: implementado]` (A2): se registra en el log, el job queda `CANCELLED` igualmente y el pool sustituye al worker; la prueba de Windows comprueba que no quedan procesos (campaña, paso 6).

## Contrato del comando

| Entrada | Efecto | Código |
|---|---|---|
| `cancel ID...` con jobs no terminados | Una job request `CANCEL` por job (y por cada hijo no terminado de una playlist), en una sola transacción | `0` |
| Algún id terminado | Se informa por cada uno; los demás se registran. Una playlist terminada con entradas no terminadas registra las de sus entradas (A4) | `0` |
| Algún id inexistente | Nada se registra | `2` |
| Base de datos bloqueada | Nada se registra | `1` |

## Postcondiciones

- **Éxito:** job `CANCELLED` (o `COMPLETED` en A3); ningún proceso de ffmpeg o deno del job sigue vivo; los archivos parciales se conservan para un posible reintento. Si el job no dejó su archivo final, suelta la reclamación de su nombre ([ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)); tras una terminación forzada (A2) la suelta `retry` o `purge`.
- **Interrupción (A6):** jobs en curso `RUNNING`, con sus parciales; ninguna job request registrada; código `130`.
- **Fallo (E1, E2):** ningún cambio en la cola.

## Transiciones

`PENDING → CANCELLED` (A1); `RUNNING → CANCELLATION_REQUESTED → CANCELLED` (flujo básico, A2); `CANCELLATION_REQUESTED → COMPLETED` (A3); `CANCELLATION_REQUESTED → CANCELLED` al recuperar tras un cierre (UC-06). Ninguna desde un estado terminado.

## Requisitos especiales

- `cancel` solo registra job requests; nunca cambia estados directamente.
- La terminación forzada no deja procesos huérfanos aunque el proceso de `run` muera.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-14, BR-16.
- **Requisitos suplementarios:** SUP-R02, SUP-C04.
- **Restricciones:** `cancel` solo registra una job request; la aplica el proceso de `run`.
- **Dependencias:** UC-03, UC-04.

## Criterios de aceptación

1. Un job `PENDING` cancelado pasa a `CANCELLED`; uno `RUNNING`, a `CANCELLED` tras detener su worker.
2. Tras cancelar, ningún proceso de ffmpeg o deno del job sigue vivo, y sus parciales se conservan.
3. Cancelar una playlist cancela sus entradas no terminadas.
4. Un job terminado no cambia (A7).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Transiciones de A1, A3, A7 y carrera entre cancelación y finalización | Cualquier sistema |
| Cancelación cooperativa con un worker real (contexto `spawn`) | Cualquier sistema |
| Paso a terminación forzada tras el plazo (A2) con `FakeProcessTreeTerminator` | Cualquier sistema |
| `WindowsProcessTreeTerminator` termina un proceso hijo y su descendiente | **Windows** |
| Cancelar mientras ffmpeg une archivos: no quedan procesos | **Windows**, al cerrar la iteración |
| A6 con `Ctrl+C` repetidos: código 130, sin traza, job `RUNNING` y reanudable | Cualquier sistema (POSIX con `SIGINT` real); **Windows** en la campaña (evento de consola) |
| A7 con `FAILED`, `SKIPPED` y `CANCELLED` procesados por `run`: el job no cambia | Cualquier sistema |
