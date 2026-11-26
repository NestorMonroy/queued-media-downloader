# UC-10: Purgar jobs terminados

- **Objetivo:** la cola queda sin los jobs terminados que ya no interesan, sin tocar ningún archivo descargado.
- **Actor principal:** User
- **Disparador:** la lista de jobs crece con jobs terminados.
- **Significativo para la arquitectura:** no
- **Estado:** aceptado (Responsable, 2026-11-26). Implementación: los escenarios originales están implementados; los ampliados tienen la marca de su flujo (`[estado: …]`).
- **Verificación:** escenarios implementados verificados con pruebas automáticas en desarrollo (Linux); validación en Windows pendiente de la campaña integral (T42 parcial, [registro](../../project-management/t42-results.md)).
- **Propuestas pendientes de aprobación (2.5.0):** A7, marcadas como propuestas; [análisis de requisitos, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).
- **Decisiones relacionadas:** [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md) (ids que no se reutilizan), [ADR-0030](../../notes/adr-0030-final-file-ownership-claims.md)
- **Diseño:** [Parte 2, §4.1](../../design/02-flows-persistence-and-operations.md#41-comandos)

## Breve descripción

El User borra de la cola los jobs `COMPLETED` y/o `CANCELLED`. Los archivos descargados nunca se tocan.

## Precondiciones

- Ninguna.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader purge [--completed] [--cancelled]`.
2. El sistema elige los estados: los indicados o, **sin opciones, `COMPLETED` y `CANCELLED`** (decisión del Responsable).
3. Por cada job en esos estados, el sistema reúne sus descendientes (si es una playlist).
4. El sistema borra los jobs en una sola transacción (con sus job requests, por `ON DELETE CASCADE`).
5. El sistema borra la carpeta de parciales de cada job borrado y las reclamaciones de nombres finales cuyo job ya no está en la cola.
6. El sistema informa cuántos jobs borró (`downloaded files are kept`) y termina con código `0`.

## Flujos alternativos

- **A1. Playlist terminada con todas sus entradas purgables** `[estado: implementado]` (paso 3): se borra con ellas; las entradas `SKIPPED` (duplicadas) se van con su playlist.
- **A2. Playlist con alguna entrada que aún requiere trabajo** `[estado: implementado]` (paso 3): `PENDING`, `RUNNING`, `CANCELLATION_REQUESTED`, `FAILED`, o un estado no elegido (por ejemplo, una entrada `CANCELLED` con `--completed`). La playlist se conserva, con esas entradas, y se informa (`Kept job N: its playlist has unfinished entries`). Sus entradas en los estados elegidos sí se borran.
- **A3. Nada que purgar** `[estado: implementado]` (paso 6): `Purged 0 jobs`; código `0`.
- **A4. `run` en ejecución en otra terminal** `[estado: implementado]` (paso 4): el borrado espera hasta `busy_timeout` (SQLite en modo WAL); los jobs en curso no son purgables.
- **A5. Purgar y borrar los archivos propios** `[estado: ausente]` (decisión D-11; el borrado de resultados es UC-25 A1, y este flujo lo aplica a los jobs purgados): `purge --delete-files` borra además el archivo final de cada job purgado, solo si el job lo escribió y conserva su reclamación con su owner token ([BR-17](../business-rules.md)). Primero muestra una vista previa (jobs, archivos y tamaño total) sin borrar nada, y solo borra con una confirmación explícita. Un archivo movido, ajeno o sin reclamación no se toca. Origen: Seal (borrar el registro con su archivo) y YTDownload-2026 (vista previa y confirmación en dos fases). A diferencia de YTDownload-2026, que borra la carpeta de salida completa, aunque sea la de una playlist entera, nunca se borra una carpeta ni un archivo que el job no escribió.
- **A6. Purga automática** `[estado: ausente]` (prioridad baja): con `purge_completed_after_days`, `run` purga al arrancar los jobs `COMPLETED` más antiguos que ese plazo. No borra archivos. Satisface la necesidad del «modo privado» de Seal (no conservar el registro de lo descargado) sin perder la protección de los archivos (ADR-0030).
- **A7. Purgar una selección** `[estado: ausente; propuesto]` (paso 1): el User purga solo los jobs terminados que selecciona; los que no son purgables se informan sin interrumpir el resto. Evidencia: YTDLnis (borrado por estado y por selección); [análisis, §15](../requirements-analysis.md#15-descubrimiento-funcional-250).

## Excepciones

- **E1. Base de datos ocupada más allá de `busy_timeout`** `[estado: implementado]` (paso 4): `the queue is busy`; no se borra nada, ni jobs ni parciales ni reclamaciones; código `1`.
- **E2. Una carpeta de parciales no se puede borrar** `[estado: implementado]` (paso 5): se registra en el log y el purge continúa. La carpeta queda huérfana sin riesgo: los ids no se reutilizan.

## Postcondiciones

- **Éxito:** ningún job en los estados elegidos, salvo los de playlists conservadas (A2). Los archivos finales siguen en su sitio y protegidos: un job nuevo no los toma como suyos (ADR-0030).
- **Fallo (E1):** ningún cambio.

## Contrato del comando

| Entrada | Estados purgados | Código |
|---|---|---|
| `purge` | `COMPLETED` y `CANCELLED` | `0` |
| `purge --completed` | `COMPLETED` | `0` |
| `purge --cancelled` | `CANCELLED` | `0` |
| `purge --completed --cancelled` | `COMPLETED` y `CANCELLED` | `0` |
| Base de datos ocupada | Ninguno | `1` |

## Restricciones

- `FAILED` no se purga: se reintenta (UC-07) o se conserva para diagnóstico.
- Un job `SKIPPED` suelto (un contenido encolado dos veces, UC-03 A1) no se purga; solo los `SKIPPED` que pertenecen a una playlist purgada.
- Tras purgar, el id de un job no se reutiliza (migración 0003).

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-17, BR-18.
- **Requisitos suplementarios:** SUP-C04.
- **Restricciones:** `FAILED` no se purga; los ids no se reutilizan.
- **Dependencias:** UC-08 (para decidir qué purgar).

## Criterios de aceptación

1. Sin opciones, se purgan los `COMPLETED` y `CANCELLED`, salvo las playlists conservadas (A2).
2. Ningún archivo final cambia (BR-18), salvo con A5 y solo los propios.
3. Con la base de datos ocupada, no se borra nada (E1).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Estados elegidos, playlists conservadas y borradas con sus duplicados | Cualquier sistema |
| Combinaciones: entrada `CANCELLED` con `--completed`, entrada `FAILED` o `RUNNING` | Cualquier sistema |
| Parciales borrados, archivos finales intactos | Cualquier sistema |
| Reclamaciones de jobs borrados o huérfanas soltadas; el archivo sigue protegido | Cualquier sistema |
| E1 con un bloqueo real de otra conexión: nada cambia, ni los parciales | Cualquier sistema |
| Purge en Windows con archivos abiertos por otro programa | **Windows**, campaña (paso 5) |
