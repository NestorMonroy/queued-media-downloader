# UC-08: Listar jobs

- **Objetivo:** el User ve el estado de la cola sin cambiar nada.
- **Actor principal:** User
- **Disparador:** el User quiere saber qué hay en la cola y cómo va.
- **Significativo para la arquitectura:** no
- **Estado:** aprobado; implementado. Los escenarios propuestos, condicionados, divergentes y defectuosos se marcan en cada flujo y se cuentan en la [matriz de completitud](../use-case-model.md#5-matriz-de-completitud).
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
- **A4. Jobs aplazados o cola en pausa** (propuesto, UC-11 y UC-14): la línea de un job aplazado añade la condición externa y, si la hay, la hora de continuación, por ejemplo `(deferred: site restriction until 00:47)`. Si la cola está en pausa o una condición afecta a toda la cola, la lista empieza con una línea que lo dice.
- **A5. Salida para otros programas** (paso 3; propuesto, prioridad media): `list --json` escribe un documento JSON con los mismos campos, en lugar de la tabla, para scripts y automatizaciones. Origen: `history list --format json` de YTDownload-2026.
- **A6. Buscar por texto** (paso 2; propuesto, prioridad baja): `list --search TEXTO` muestra solo los jobs cuyo título o URL contienen el texto. Origen: la búsqueda del historial de YTDownload-2026 y de Seal.

## Excepciones

- **E1. Estado no válido:** argparse lo rechaza; código `2`.
- **E2. `--parent` de un job inexistente:** código `2`.
- **E3. Base de datos ocupada al abrirla o migrarla:** `the queue is busy`, código `1`.

## Postcondiciones

- La cola no cambia (sí puede aplicarse una migración pendiente al abrir la base de datos, como en cualquier comando).

## Reglas, requisitos y restricciones asociados

- **Reglas:** ninguna.
- **Requisitos suplementarios:** SUP-F01, SUP-C04.
- **Restricciones:** solo lectura.
- **Dependencias:** UC-01.

## Criterios de aceptación

1. `list` nunca cambia la base de datos.
2. Cada job aparece con su id, estado, tipo e intentos; un filtro por estado solo muestra jobs en ese estado.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Filtros por estado y padre, cola vacía | Cualquier sistema |
| Salida en una consola de Windows (anchos, caracteres no ASCII) | **Windows**, campaña (paso 12) |
