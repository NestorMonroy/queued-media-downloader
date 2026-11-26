# UC-09: Ver un job

- **Objetivo:** el User ve todos los datos de un job: su archivo o por qué falló.
- **Actor principal:** User
- **Disparador:** el User quiere saber dónde quedó un contenido o por qué falló.
- **Significativo para la arquitectura:** no
- **Estado:** aprobado; implementado. Los escenarios propuestos, condicionados, divergentes y defectuosos se marcan en cada flujo y se cuentan en la [matriz de completitud](../use-case-model.md#5-matriz-de-completitud).
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
- **A2. Job fallido** (paso 3): añade la failure reason y su mensaje. **Parcial:** indicar si reintentar puede servir y qué acción lo resuelve está propuesto (SUP-U05).
- **A3. Playlist** (paso 3): añade el número de hijos por estado.
- **A4. Job aplazado** (propuesto, UC-11 y UC-14): añade el sitio, la condición externa, la hora de continuación si la hay y el número de aplazamientos seguidos, o que la cola está en pausa.
- **A5. Salida para otros programas** (paso 3; propuesto, prioridad media): `show ID --json`, como UC-08 A5.
- **A6. Resultados del job** (paso 3; propuesto, D-15): añade la lista de resultados registrados (tipo, ruta y si existe); el detalle y la administración están en UC-25.

## Excepciones

- **E1. Job inexistente:** código `2`.
- **E2. Base de datos ocupada al abrirla o migrarla:** `the queue is busy`, código `1`.

## Postcondiciones

- La cola no cambia.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-22.
- **Requisitos suplementarios:** SUP-U01, SUP-U05 (propuesto), SUP-C04.
- **Restricciones:** solo lectura.
- **Dependencias:** UC-01.

## Criterios de aceptación

1. `show` nunca cambia la base de datos.
2. Un job `COMPLETED` muestra su archivo final; uno `FAILED`, su motivo y su mensaje.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Datos de un job, de un hijo, de un fallo y de una playlist | Cualquier sistema |
| Job inexistente | Cualquier sistema |
| Salida en una consola de Windows | **Windows**, campaña (paso 5) |
