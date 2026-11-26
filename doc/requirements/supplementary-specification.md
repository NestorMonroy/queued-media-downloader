# Especificación complementaria

- **Fase RUP:** Inicio
- **Versión:** 1.0 (borrador para revisión)
- **Fecha:** 2026-11-23

Requisitos que no pertenecen a un caso de uso concreto, organizados según FURPS+. Cada requisito tiene un identificador para trazarlo en pruebas e iteraciones.

---

## Funcionalidad (transversal)

| ID | Requisito | Origen |
|---|---|---|
| SUP-F01 | La salida de la línea de comandos y los logs están en inglés | [ADR-0011](../notes/adr-0011-code-conventions.md) |
| SUP-F02 | Códigos de salida: `0` todo correcto, `1` algún job falló o la cola está ocupada o no se puede abrir, `2` error de uso o de configuración, `130` `run` interrumpido con `Ctrl+C` (decisión del Responsable, T49) | [Parte 2, §4.1](../design/02-flows-persistence-and-operations.md#41-comandos) |
| SUP-F03 | La configuración se toma de argumentos, variables de entorno `QUEUED_MEDIA_DOWNLOADER_*`, `config.toml` y valores por defecto, en ese orden de prioridad | [Parte 2, §4.2](../design/02-flows-persistence-and-operations.md#42-configuración) |

## Usabilidad

| ID | Requisito |
|---|---|
| SUP-U01 | Todo mensaje de error indica la acción concreta para corregirlo (por ejemplo, `git lfs pull`, o la clave de configuración no válida) |
| SUP-U02 | El progreso se muestra como máximo cada `progress_interval_seconds` |
| SUP-U03 | La instalación completa se describe en el README en no más de cuatro comandos |

## Fiabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-R01 | Un cierre inesperado no pierde jobs: al volver a ejecutar `run`, la cola se recupera y las descargas continúan desde lo descargado | [ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md) |
| SUP-R02 | Cancelar o terminar un worker nunca deja procesos de ffmpeg o deno en ejecución, aunque el proceso principal muera | [ADR-0013](../notes/adr-0013-process-tree-terminator-abstraction.md) |
| SUP-R03 | El fallo de un job no detiene el resto de la cola | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-R04 | Un worker que muere de forma inesperada se detecta y se reemplaza; su job queda `FAILED` con `WORKER_CRASHED` | [Parte 2, §3.2](../design/02-flows-persistence-and-operations.md#32-ciclo-de-vida-del-worker) |
| SUP-R05 | Un mismo contenido no se descarga dos veces mientras haya un job activo para su media key | [ADR-0012](../notes/adr-0012-no-download-archive-no-database-triggers.md) |

## Rendimiento y recursos

| ID | Requisito | Origen |
|---|---|---|
| SUP-P01 | Concurrencia por defecto: 1 worker; configurable | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-P02 | La memoria de un worker no crece con el número de entradas de una playlist | [ADR-0009](../notes/adr-0009-playlist-expansion-into-jobs.md) |
| SUP-P03 | El progreso de las descargas no se escribe en la base de datos | [Parte 1, §5](../design/01-architecture.md#5-job-events) |
| SUP-P04 | **Presupuesto de memoria** (proceso principal + 1 worker, sin contar ffmpeg ni deno): **pendiente**: se fija con la medición en Windows de la campaña T42 (paso 13; trasladada desde E1). Referencia de la medición en Linux: ~38 MB por proceso con yt-dlp cargado | Medición del análisis (`scripts/measure_footprint.py`, espacio de trabajo `yt-dlp-gui-clone`) |

## Mantenibilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-S01 | Actualizar yt-dlp es un procedimiento documentado: cambiar la versión fijada, ejecutar las pruebas de contrato, publicar | [ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md), [procedimiento](../process/yt-dlp-update-procedure.md) |
| SUP-S02 | Todo el código cumple las reglas de importación (`lint-imports`), el formato y el linter (Ruff) y la verificación de tipos estricta (mypy) | [ADR-0017](../notes/adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S03 | Identificadores en inglés según el vocabulario; docstrings y comentarios en español | [ADR-0011](../notes/adr-0011-code-conventions.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S04 | Las reglas de la cola (`jobs/`, `job_queue/`) se prueban sin yt-dlp, sin SQLite y sin procesos | [Parte 1, §1](../design/01-architecture.md#1-principios-de-diseño) |

## Restricciones de diseño e implementación (+)

| ID | Restricción | Origen |
|---|---|---|
| SUP-C01 | Windows 10/11 x64; Python ≥3.11 gestionado por uv | [ADR-0003](../notes/adr-0003-packaging-with-uv-and-pyproject.md), [ADR-0004](../notes/adr-0004-windows-x64-target-platform.md) |
| SUP-C02 | yt-dlp 2026.11.23 como librería (antes 2026.10.26; ver el seguimiento de ADR-0002); solo los módulos `yt_dlp_*` lo importan | [ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md), [ADR-0017](../notes/adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md) |
| SUP-C03 | ffmpeg 9.0 LGPL compartido incluido en `vendor/ffmpeg/` con Git LFS | [ADR-0018](../notes/adr-0018-ffmpeg-build-selection.md) |
| SUP-C04 | Persistencia en SQLite; solo el proceso de `run` cambia el estado de los jobs | [ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md) |
| SUP-C05 | Sin servidor de integración continua; las pruebas se ejecutan con `uv run pytest` | [ADR-0021](../notes/adr-0021-tdd-and-windows-validation-without-ci.md) |

## Licencias

| ID | Requisito | Origen |
|---|---|---|
| SUP-L01 | Código del proyecto bajo The Unlicense | [ADR-0007](../notes/adr-0007-project-license-unlicense.md) |
| SUP-L02 | `vendor/ffmpeg/` incluye el texto de la LGPL y la referencia al código fuente de la build exacta | [ADR-0018](../notes/adr-0018-ffmpeg-build-selection.md) |
| SUP-L03 | Todo material incluido en el repositorio tiene su distribución confirmada (cumplido para `doc/reference/`) | [ADR-0007](../notes/adr-0007-project-license-unlicense.md), [ADR-0025](../notes/adr-0025-reference-material-distribution.md) |
