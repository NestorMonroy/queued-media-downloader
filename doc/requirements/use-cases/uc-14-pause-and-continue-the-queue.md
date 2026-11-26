# UC-14: Pausar y continuar la cola

- **Objetivo:** el User deja libre la conexión o el equipo durante un rato, desde cualquier terminal, sin cancelar nada ni perder la cola, y la cola continúa cuando él lo indica.
- **Actor principal:** User
- **Disparador:** el User necesita la conexión o el equipo para otra cosa (por ejemplo, una videollamada).
- **Prioridad:** baja (hoy hay una alternativa: `Ctrl+C` en la terminal de `run` y volver a ejecutarlo)
- **Significativo para la arquitectura:** no (reutiliza las job requests de UC-05 y la interrupción de UC-05 A6)
- **Estado:** propuesto; decisión D-6 pendiente ([análisis](../unattended-operation-analysis.md))

## Breve descripción

El User pausa la cola con un comando, desde cualquier terminal, y la continúa más tarde con otro. Como `cancel`, el comando solo registra la petición; el proceso de `run` la aplica. Una interfaz gráfica futura usaría el mismo mecanismo.

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

- **A1. `pause --now`** (paso 1): los jobs en curso se detienen como con un `Ctrl+C` y se reanudan al continuar ([BR-10](../business-rules.md)).
- **A2. `run` no está en ejecución** (paso 3): la pausa queda guardada; un `run` posterior arranca en pausa y lo avisa.
- **A3. `run` con la cola en pausa y sin `--keep-waiting`:** `run` espera a la continuación con el aviso periódico; `Ctrl+C` lo termina con código `130`.
- **A4. `pause` con la cola ya en pausa, o `resume` sin pausa:** el sistema informa de que no hay cambios y termina con código `0`.
- **A5. `list` y `show` durante la pausa** (UC-08, UC-09): muestran que la cola está en pausa.

## Excepciones

- **E1. Base de datos ocupada más allá de `busy_timeout`:** como UC-05 E2; nada se registra y el código es `1`.

## Garantías

- **De éxito:** ningún job cambió de estado por la pausa; la cola continuó al pedirlo el User.
- **Mínima:** la pausa nunca cancela un job ni borra archivos parciales.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Pasos 1 a 6, A2 y A4 con un pool guionizado | Cualquier sistema |
| A1 con workers reales: detención y reanudación | Cualquier sistema |
| `pause --now` en Windows (evento de consola) | **Windows**, campaña |
