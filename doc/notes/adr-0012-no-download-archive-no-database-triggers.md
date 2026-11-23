# ADR-0012: Sin `download_archive` ni triggers con reglas de negocio

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Ajusta:** [ADR-0009](adr-0009-playlist-expansion-into-jobs.md) (que mencionaba `download_archive` junto a la restricción única)

## Contexto

yt-dlp puede evitar descargas repetidas con `download_archive`. En el código de la versión 2026.10.26:
- El parámetro acepta *"A set, or the name of a file"*.
- yt-dlp solo usa `id in archive`, `archive.add(id)` y la evaluación `if not archive`.
- El identificador tiene la forma `"<extractor en minúsculas> <id>"`.
- `archive.add()` se invoca dentro del proceso que descarga, es decir, en el worker.

El proyecto ya evita duplicados con un índice único parcial en SQLite (`unique_active_download_per_media`), aplicado al crear los jobs durante la expansión.

## Opciones consideradas

1. **Usar el archivo de `download_archive` además de la base de datos.** Dos registros de lo mismo que habría que sincronizar.
2. **Adaptador que implemente la interfaz de `download_archive` sobre la base de datos.** Un solo registro; viable porque yt-dlp acepta cualquier objeto con `__contains__`, `add` y `__bool__`.
3. **Triggers de SQLite** para sincronizar estados. SQLite no tiene procedimientos almacenados, pero sí triggers.
4. **No usar `download_archive`.** La base de datos es la única fuente de verdad.

## Decisión

**Opción 4.** No se usa `download_archive` ni triggers que contengan reglas de negocio.

Evaluación con las [guías de clean code](../reference/clean-code-guidelines/README.md):
- **DRY:** la opción 1 duplica conocimiento. Las opciones 2 y 4 lo cumplen igual.
- **YAGNI / KISS:** los duplicados ya se descartan al expandir. Cuando yt-dlp consultara el archivo, la decisión ya estaría tomada: el adaptador de la opción 2 nunca cambiaría el resultado.
- **Separación de responsabilidades:** con la opción 2, `archive.add()` escribiría en la base de datos desde un worker, contra la regla de un solo escritor ([ADR-0010](adr-0010-sqlite-persistent-queue.md)). Convertir `add()` en una operación vacía sería sorprendente (**menor sorpresa**).
- **Triggers:** pondrían reglas de transición en SQL, duplicando las de `download_queue/job_lifecycle.py` (**DRY**, **separación de responsabilidades**), con efectos ocultos al guardar (**menor sorpresa**) que las pruebas de las reglas no verían.

## Consecuencias

- Las reglas de negocio viven solo en el código Python de `download_queue/`; la base de datos solo guarda.
- **Extensión prevista, no implementada:** si hace falta importar el `download_archive` de alguien que ya usaba yt-dlp por consola, se añadirá un caso de uso `import_download_archive` que lea el archivo y cree jobs `COMPLETED`. Se añade sin modificar lo existente (**abierto/cerrado**).
