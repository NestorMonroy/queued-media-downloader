# UC-14: Controlar temporalmente la ejecución de la cola

- **Objetivo:** el User suspende o detiene de forma ordenada la ejecución de la cola desde cualquier terminal, sin cancelar ningún job ni perder lo descargado, y la reanuda cuando quiere.
- **Actor principal:** User
- **Disparador:** el User necesita la conexión o el equipo para otra cosa, o quiere que `run` termine al acabar lo que está haciendo.
- **Prioridad:** baja. Hoy hay una alternativa: `Ctrl+C` en la terminal de `run` (UC-05 A6) y volver a ejecutarlo.
- **Significativo para la arquitectura:** no (reutiliza las job requests de UC-05 y la interrupción de UC-05 A6)
- **Estado:** propuesto; **no implementado**. Decisión D-6 pendiente ([análisis de requisitos](../requirements-analysis.md#9-decisiones-pendientes)).
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

- **A1. `pause --now`** (paso 1): los jobs en curso se detienen como con un `Ctrl+C` y se reanudan al continuar (BR-10).
- **A2. `stop`** (paso 1): `run` deja de enviar jobs, espera a que terminen los que están en curso y termina con código `0`, o `1` si algún job falló. Los jobs pendientes quedan para el siguiente `run`.
- **A3. `run` no está en ejecución** (paso 3): la pausa queda guardada; un `run` posterior arranca en pausa y lo avisa. Un `stop` sin `run` activo no tiene efecto, y el sistema lo informa.
- **A4. `run` con la cola en pausa y sin `--keep-waiting`:** `run` espera la continuación con el aviso periódico. Si el User pulsa `Ctrl+C`, `run` termina con código `130`.
- **A5. `pause` con la cola ya en pausa, o `resume` sin pausa:** el sistema informa de que no hay cambios y termina con código `0`.
- **A6. `list` y `show` durante la pausa** (UC-08, UC-09): indican que la cola está en pausa.

## Excepciones

- **E1. Base de datos ocupada más allá de `busy_timeout`:** como UC-05 E2; no se registra nada y el código es `1`.

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
