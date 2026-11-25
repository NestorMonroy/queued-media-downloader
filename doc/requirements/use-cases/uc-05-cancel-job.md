# UC-05: Cancelar un job

- **Actor principal:** User
- **Significativo para la arquitectura:** sí
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

- **A1. Job `PENDING`** (paso 4): pasa directamente a `CANCELLED`.
- **A2. Sin confirmación en `cancellation_grace_seconds`** (paso 5): por ejemplo, durante la extracción o mientras ffmpeg une archivos. El sistema termina el process tree del worker (worker, ffmpeg y deno), marca el job `CANCELLED` y arranca un worker de reemplazo.
- **A3. El job termina antes de ver la bandera** (paso 5): llega `JobCompleted` y el job queda `COMPLETED`.
- **A4. Cancelar una playlist** (paso 2): se registra `CANCEL` para la expansión y para cada hijo no terminado.
- **A5. `run` no está en ejecución** (paso 3): la job request se procesa al arrancar el siguiente `run`.
- **A6. `Ctrl+C` durante `run`:** el sistema deja de enviar jobs y detiene los jobs en curso con el mismo mecanismo que la cancelación (pasos 5 y A2), pero sin cancelarlos: siguen `RUNNING`, con sus archivos parciales. Un segundo `Ctrl+C` termina los workers de inmediato. `run` termina con código `130`, y los jobs interrumpidos se recuperan y se reanudan en el siguiente `run` (UC-06; interrupción recuperable, [ADR-0029](../../notes/adr-0029-process-tree-termination-on-windows.md)).
- **A7. Job ya terminado** (`COMPLETED`, `SKIPPED`, `CANCELLED`): la job request se marca procesada sin cambios y se informa al User.

## Postcondiciones

- **Éxito:** job `CANCELLED` (o `COMPLETED` en A3); ningún proceso de ffmpeg o deno del job sigue vivo; los archivos parciales se conservan para un posible reintento.

## Requisitos especiales

- `cancel` solo registra job requests; nunca cambia estados directamente.
- La terminación forzada no deja procesos huérfanos aunque el proceso de `run` muera.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Transiciones de A1, A3, A7 y carrera entre cancelación y finalización | Cualquier sistema |
| Cancelación cooperativa con un worker real (contexto `spawn`) | Cualquier sistema |
| Paso a terminación forzada tras el plazo (A2) con `FakeProcessTreeTerminator` | Cualquier sistema |
| `WindowsProcessTreeTerminator` termina un proceso hijo y su descendiente | **Windows** |
| Cancelar mientras ffmpeg une archivos: no quedan procesos | **Windows**, al cerrar la iteración |
