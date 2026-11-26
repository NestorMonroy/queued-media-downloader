# UC-08: Listar jobs

- **Objetivo:** el User ve el estado de la cola sin cambiar nada.
- **Actor principal:** User
- **Disparador:** el User quiere saber qué hay en la cola y cómo va.
- **Significativo para la arquitectura:** no
- **Diseño:** [Parte 2, §4.1](../../design/02-flows-persistence-and-operations.md#41-comandos)

## Breve descripción

El User consulta los jobs de la cola, opcionalmente filtrados por estado o por playlist padre. No se modifica nada.

## Precondiciones

- Ninguna (con una cola vacía, el sistema lo indica).

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader list [--status STATUS] [--parent JOB_ID]`.
2. El sistema lee los jobs en orden de creación, con los filtros indicados.
3. El sistema escribe una línea por job: id, tipo, estado, título (o la URL, si aún no tiene título) y, si falló, su failure reason. Termina con código `0`.

## Flujos alternativos

- **A1. Ningún job coincide** (paso 3): escribe `No jobs`; código `0`.
- **A2. `--parent`** (paso 2): solo los hijos directos de esa expansión.
- **A3. `run` escribe a la vez en otra terminal** (paso 2): la lectura funciona (SQLite en modo WAL) y refleja el último estado confirmado.
- **A4. Jobs que esperan** (propuesto, UC-11 a UC-14): la línea de un job pendiente de un sitio en espera añade el motivo y la hora de continuación, por ejemplo `(waiting: site block until 00:47)`. Si `run` espera a la red o al disco, o la cola está en pausa, la lista empieza con una línea que lo dice.

## Excepciones

- **E1. Estado no válido:** argparse lo rechaza; código `2`.
- **E2. `--parent` de un job inexistente:** código `2`.
- **E3. Base de datos ocupada al abrirla o migrarla:** `the queue is busy`, código `1`.

## Postcondiciones

- La cola no cambia (sí puede aplicarse una migración pendiente al abrir la base de datos, como en cualquier comando).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Filtros por estado y padre, cola vacía | Cualquier sistema |
| Salida en una consola de Windows (anchos, caracteres no ASCII) | **Windows**, campaña (paso 12) |
