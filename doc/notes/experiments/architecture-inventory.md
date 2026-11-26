# Experimento: inventario estructural y grafo de componentes

- **Fecha:** 2026-11-26
- **Script:** `scripts/experiments/architecture_inventory.py` (no es código de producción)
- **Resultados en bruto:** [architecture-inventory-linux.json](architecture-inventory-linux.json)
- **Ambiente:** Linux x86_64, Python 3.13.18, grimp 3.20 (la librería de import-linter 2.17); commit base `b4ac64a`
- **Aislamiento:**
  - solo lee el código fuente con `ast` y grimp;
  - no importa el paquete, no abre la base de datos y no escribe fuera de `--output`.
- **Consumidor:** [diseño, Parte 3, §2](../../design/03-target-architecture-and-evolution.md#2-arquitectura-vigente)

| Campo | Contenido |
|---|---|
| Pregunta | ¿Qué componentes dependen de mecanismos que varían entre interfaces o plataformas, y cómo es el grafo real entre componentes? |
| Hipótesis | Las reglas y los casos de uso (`jobs`, `job_queue`) no importan mecanismos variables. Estos se concentran en `workers`, `job_storage`, `ffmpeg_discovery` y `command_line` |
| Entradas | `queued_media_downloader/` y `tests/` en `b4ac64a` más los cambios de esta rama, que no tocan el código productivo |
| Procedimiento | `uv run python scripts/experiments/architecture_inventory.py --output RUTA` |
| Resultado esperado | Ningún mecanismo variable en `jobs` ni en `job_queue`; un grafo sin ciclos |
| Resultado observado | Coincide con el esperado (detalle abajo) |
| Código de salida | 0 (dos ejecuciones con el mismo grafo) |
| Contrato afectado | Reglas AR-02 y AR-04 (activadas); A-1 a A-8 de la Parte 3 |
| Reproducibilidad | Determinista para un commit dado |

**Resultado observado:**
- 85 módulos y 6.896 líneas;
- 397 funciones de prueba (pytest ejecuta 593 por la parametrización; regenerado en la instrucción 2.4.0 sin cambios en el código del producto);
- 10 marcas `windows`;
- mecanismos variables:
  - `argparse` solo en `command_line` (8 módulos);
  - `sqlite3` en `job_storage` (5), `command_line` (1) y `diagnostics` (1);
  - `multiprocessing` (3), `ctypes` (2) y `signal` (2) en `workers`;
  - `subprocess` en `ffmpeg_discovery` (1);
  - `tomllib` en `configuration` (1);
  - `jobs` y `job_queue`: ninguno;
- grafo: sin imports mutuos; `job_queue` depende de `workers` y de `media_extraction` solo por sus API públicas.

**Limitaciones:**
- No detecta imports dinámicos ni dependencias operacionales. No hay imports dinámicos: `importlib` solo se usa para metadatos (`importlib.metadata`) y recursos (`importlib.resources`), no para importar módulos. yt-dlp lanza ffmpeg y deno con `Popen`; esas se documentan por inspección en la Parte 3, §2.2.
- Las clases se clasifican por sus bases y decoradores directos.
