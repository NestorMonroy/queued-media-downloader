# UC-02: Encolar contenido

- **Actor principal:** User
- **Significativo para la arquitectura:** sí
- **Decisiones relacionadas:** [ADR-0009](../../notes/adr-0009-playlist-expansion-into-jobs.md), [ADR-0010](../../notes/adr-0010-sqlite-persistent-queue.md)
- **Diseño:** [Parte 2, §1.1](../../design/02-flows-persistence-and-operations.md#11-encolar)

## Breve descripción

El User añade una o varias URLs a la cola, con sus download options. El sistema crea un job de expansión por URL, sin extraer ni descargar nada.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `uv run queued-media-downloader enqueue URL... [--format SELECTOR] [--audio-only] [--download-directory DIR]`.
2. El sistema construye las download options combinando los argumentos con la configuración (argumentos > variables de entorno > `config.toml` > valores por defecto).
3. El sistema valida cada URL (forma de URL) y las download options.
4. Para cada URL, el sistema crea un job `EXPANSION` en estado `PENDING` con sus download options fijadas.
5. El sistema muestra el id de cada job creado (por ejemplo, `Queued job 42`) y termina con código `0`.

## Flujos alternativos

- **A1. URL no válida** (paso 3): el sistema indica cuál es, no crea ningún job de esa invocación y termina con código `2`.
- **A2. `run` en ejecución en otra terminal** (paso 4): la creación funciona igual (SQLite en modo WAL); el proceso de `run` toma el job en su siguiente ciclo.
- **A3. Base de datos bloqueada más allá de `busy_timeout`** (paso 4): el sistema informa del bloqueo y termina con código `1` sin crear jobs.

## Postcondiciones

- **Éxito:** un job `EXPANSION` `PENDING` por URL. Si después cambia la configuración, esos jobs conservan sus download options.

## Requisitos especiales

- `enqueue` no accede a la red: responde de inmediato aunque la conexión sea lenta.
- `enqueue` solo crea jobs; nunca cambia el estado de jobs existentes ([Parte 2, §2.4](../../design/02-flows-persistence-and-operations.md#24-escritura-desde-varios-procesos)).

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Combinación de argumentos y configuración | Cualquier sistema |
| URL no válida: no se crea ningún job | Cualquier sistema |
| Varias URLs en una invocación | Cualquier sistema |
| `enqueue` mientras otro proceso escribe en la base de datos | Cualquier sistema |
