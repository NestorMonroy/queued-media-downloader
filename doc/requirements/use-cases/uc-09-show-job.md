# UC-09: Ver un job

- **Actor principal:** User
- **Significativo para la arquitectura:** no
- **Diseño:** [Parte 2, §4.1](../../design/02-flows-persistence-and-operations.md#41-comandos)

## Breve descripción

El User consulta todos los datos de un job; si es una playlist, también el resumen de sus hijos por estado. No se modifica nada.

## Precondiciones

- Existe el job indicado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader show JOB_ID`.
2. El sistema lee el job.
3. El sistema escribe: id, tipo, estado, URL, título, intento (`attempt_count + 1`), formato elegido (o el format selector), solo audio, carpeta de descargas y archivo final. Termina con código `0`.

## Flujos alternativos

- **A1. Hijo de una playlist** (paso 3): añade la playlist padre, su título y el índice de la entrada.
- **A2. Job fallido** (paso 3): añade la failure reason y su mensaje.
- **A3. Playlist** (paso 3): añade el número de hijos por estado.

## Excepciones

- **E1. Job inexistente:** código `2`.
- **E2. Base de datos ocupada al abrirla o migrarla:** `the queue is busy`, código `1`.

## Postcondiciones

- La cola no cambia.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Datos de un job, de un hijo, de un fallo y de una playlist | Cualquier sistema |
| Job inexistente | Cualquier sistema |
| Salida en una consola de Windows | **Windows**, campaña (paso 5) |
