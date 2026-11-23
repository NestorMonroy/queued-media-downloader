# UC-04: Expandir una playlist

- **Actor principal:** User
- **Actor secundario:** Media site
- **Significativo para la arquitectura:** sí
- **Decisiones relacionadas:** [ADR-0009](../../notes/adr-0009-playlist-expansion-into-jobs.md), [ADR-0012](../../notes/adr-0012-no-download-archive-no-database-triggers.md)
- **Diseño:** [Parte 2, §1.2](../../design/02-flows-persistence-and-operations.md#12-expansión)

## Breve descripción

Durante la ejecución de la cola, un job de expansión resulta ser una playlist o un canal. El sistema recorre sus entradas por lotes y crea un job hijo por entrada, con el contexto de la playlist, sin cargar la playlist completa en memoria.

## Precondiciones

- `run` en ejecución (UC-03, pasos 1 a 4) y un job `EXPANSION` `RUNNING` cuya URL es una playlist.

## Flujo básico

1. El worker extrae la URL sin resolver sus entradas (`process=False`).
2. El worker recorre las playlist entries de forma perezosa, calculando `playlist_index` al enumerar.
3. Por cada lote (por ejemplo, de 50 entradas), el worker publica `PlaylistEntriesFound`.
4. El sistema crea un job hijo `DOWNLOAD` `PENDING` por entrada, con su `PlaylistContext` (id, título, índice y número de entradas de la playlist).
5. Se repiten los pasos 3 y 4 hasta agotar las entradas.
6. El worker publica `JobCompleted`; la expansión pasa a `COMPLETED`.
7. Los jobs hijos se descargan como en UC-03 (pasos 6 a 11), en la carpeta de su playlist ([ADR-0028](../../notes/adr-0028-playlist-child-output-template.md)).

## Flujos alternativos

- **A1. Entrada que es otra playlist** (paso 4): por ejemplo, las pestañas de un canal. Se crea un hijo `EXPANSION`, que se expandirá a su vez.
- **A2. Entrada duplicada** (paso 4): ya existe un job `DOWNLOAD` activo con la misma media key. El hijo se crea como `SKIPPED`.
- **A3. Entrada no disponible** (privada o eliminada) (paso 4): el hijo se crea como `SKIPPED`, no como `FAILED`.
- **A4. Contenido `multi_video`** (paso 1): se trata como un solo contenido; continúa como UC-03 desde el paso 5.
- **A5. Cancelación durante la expansión:** ver UC-05. Los hijos ya creados quedan en la cola, salvo que se cancele la playlist entera.
- **A6. Fallo de red a mitad de la expansión** (paso 2): la expansión pasa a `FAILED`; los hijos ya creados se conservan. Al reintentarla (UC-07), los duplicados quedan `SKIPPED` (A2).

## Postcondiciones

- **Éxito:** la expansión está `COMPLETED` y existe un job hijo por cada playlist entry; el estado de la playlist se deriva de sus hijos.

## Requisitos especiales

- La memoria del worker no crece con el número de entradas de la playlist.
- La plantilla de salida de los hijos la construye el proyecto con el contexto guardado; no se usa `extra_info` de yt-dlp.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Creación de hijos por lotes, duplicados y no disponibles (A2, A3) | Cualquier sistema |
| Playlists anidadas (A1) | Cualquier sistema |
| `output_template_builder`: escapado de `%`, saneado y longitud | Cualquier sistema (`PureWindowsPath` para las reglas de Windows) |
| `process=False` itera de forma perezosa un canal grande | Cualquier sistema, con red (marcador `network`), en la iteración E2 |
