# UC-14: Controlar temporalmente la ejecución de la cola

- **Objetivo:** el User suspende o detiene de forma ordenada la ejecución de la cola desde cualquier terminal, sin cancelar ningún job ni perder lo descargado, y la reanuda cuando quiere.
- **Actor principal:** User
- **Disparador:** el User necesita la conexión o el equipo para otra cosa, o quiere que `run` termine al acabar lo que está haciendo.
- **Prioridad:** baja. Hoy hay una alternativa: `Ctrl+C` en la terminal de `run` (UC-05 A6) y volver a ejecutarlo.
- **Significativo para la arquitectura:** no (reutiliza las job requests de UC-05 y la interrupción de UC-05 A6)
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: ausente (la interrupción con `Ctrl+C` de UC-05 A6 sí existe). Condición técnica: D-6.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Propuestas pendientes de aprobación (2.5.0):** A7, A8 y E2, marcadas como propuestas; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Origen:**
  - referencias: Seal (estados reanudables de sus tareas) y la interfaz gráfica futura que reutilizará el motor ([visión](../vision.md));
  - análisis de continuidad: [análisis de requisitos, §7](../requirements-analysis.md#7-continuidad-reintentos-y-recuperación).
- **Historial:** antes "Pausar y continuar la cola". El nombre describía la solución; la necesidad es controlar temporalmente la ejecución.

## Breve descripción

`pause` deja de enviar jobs; `resume` vuelve a enviarlos; `stop` pide a `run` que termine en cuanto acaben los jobs en curso. Como `cancel`, estos comandos solo registran la petición: el proceso de `run` la aplica (SUP-C04).

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader pause`.
2. El sistema registra la pausa, informa (`Queue paused; running jobs will finish`) y termina con código `0`.
3. El proceso de `run` deja de enviar jobs y deja terminar los que están en curso ([BR-10](../business-rules.md)). Avisa de que la cola está en pausa ([BR-11](../business-rules.md)).
4. El User ejecuta `uv run queued-media-downloader resume`.
5. El sistema registra la continuación, informa (`Queue resumed`) y termina con código `0`.
6. El proceso de `run` vuelve a enviar jobs.

## Flujos alternativos

- **A1. `pause --now`** `[estado: ausente]` (paso 1): los jobs en curso se detienen como con un `Ctrl+C` y se reanudan al continuar (BR-10).
- **A2. `stop`** `[estado: ausente]` (paso 1): `run` deja de enviar jobs, espera a que terminen los que están en curso y termina con código `0`, o `1` si algún job falló. Los jobs pendientes quedan para el siguiente `run`.
- **A3. `run` no está en ejecución** `[estado: ausente]` (paso 3): la pausa queda guardada; un `run` posterior arranca en pausa y lo avisa. Un `stop` sin `run` activo no tiene efecto, y el sistema lo informa.
- **A4. `run` con la cola en pausa y sin `--keep-waiting`:** `[estado: ausente]` `run` espera la continuación con el aviso periódico. Si el User pulsa `Ctrl+C`, `run` termina con código `130`.
- **A5. `pause` con la cola ya en pausa, o `resume` sin pausa:** `[estado: ausente]` el sistema informa de que no hay cambios y termina con código `0`.
- **A6. `list` y `show` durante la pausa** `[estado: ausente]` (UC-08, UC-09): indican que la cola está en pausa.
- **A7. Pausar o reanudar un job concreto** `[estado: ausente; propuesto]` (paso 1): el User pausa un job pendiente o activo sin pausar la cola. Uno activo se interrumpe como en A1 y conserva sus parciales; el job pausado deja de ser elegible hasta que el User lo reanuda. Evidencia: NewPipe (`pauseMission` y `resumeMission` en `DownloadManager`) y VidBee (estado `paused`; `:download pause <id> --reason` en su CLI de `d483045`); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **A8. Cambiar el orden de ejecución** `[estado: ausente; propuesto]` (paso 1): el User mueve un job pendiente al principio, al final o a una posición de la cola. El orden se conserva tras un reinicio y solo decide entre jobs elegibles ([BR-46](../business-rules.md)). Evidencia: YTDLnis (`queueOrder`, `putAtTopOfQueue`, `putQueueDownloadAtPosition`) y VidBee (prioridad por procedencia con orden de llegada como desempate).

## Excepciones

- **E1. Base de datos ocupada más allá de `busy_timeout`:** `[estado: ausente]` como UC-05 E2; no se registra nada y el código es `1`.
- **E2. Orden pedido para un job que no está pendiente** `[estado: ausente; propuesto]` (A8): el job está activo o terminado. El sistema lo informa y no cambia nada.

## Garantías

- **De éxito:** ningún job cambió de estado por la pausa; la cola continuó cuando el User lo pidió.
- **Mínima:** la pausa y la detención nunca cancelan un job ni borran archivos parciales.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-10 y BR-11.
- **Requisitos suplementarios:** SUP-C04 y SUP-U04.
- **Restricciones:** solo el proceso de `run` cambia el estado de los jobs.
- **Dependencias:** UC-05 (job requests e interrupción) y UC-06.

## Criterios de aceptación

1. Tras `pause`, `run` no envía ningún job nuevo; los que estaban en curso terminan, salvo con `--now`.
2. Tras `resume`, `run` vuelve a enviar jobs sin reiniciarse.
3. Tras `stop`, `run` termina en cuanto acaban los jobs en curso, sin cancelar ninguno.
4. Ninguna de las tres órdenes cambia el estado de un job ni borra archivos.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Pasos 1 a 6, A2, A3 y A5 con un pool guionizado | Cualquier sistema |
| A1 con workers reales: detención y reanudación | Cualquier sistema |
| `pause --now` en Windows (evento de consola) | **Windows**, campaña |
