# ADR-0016: Paquetes por componente y paquete en la raíz del proyecto

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** [ADR-0017](adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md) mueve `composition_root.py` a `command_line/`, define la API pública de cada componente en su `__init__.py` y comprueba estas reglas con `import-linter`.
- **Reemplaza:** la estructura de paquetes de [ADR-0014](adr-0014-use-case-structure-and-vocabulary.md) (el vocabulario de ese ADR sigue vigente)
- **Ajusta:** la carpeta del proyecto definida en [ADR-0015](adr-0015-project-and-package-name.md)

## Contexto

ADR-0014 organizó el código en `use_cases/` y `download_queue/`, siguiendo *Clean Architecture*. Ningún proyecto analizado usa esa estructura, y el nombre `use_cases/` comete el mismo error que `domain/` o `application/`: es una categoría técnica, no una intención (principio de nombres #9).

La estructura de yt-dlp 2026.10.26:
- Un paquete por componente del dominio de la descarga de medios: `extractor/` (971 archivos), `downloader/` (17), `postprocessor/` (10), `networking/` (10).
- Cada paquete contiene su contrato (`InfoExtractor`, `FileDownloader`, `PostProcessor`, `RequestHandler`) y sus implementaciones, y una función que elige la implementación (`gen_extractor_classes`, `get_suitable_downloader`, `get_postprocessor`).
- El paquete está en la raíz del repositorio (`yt-dlp/yt_dlp/`), sin `src/`; las pruebas están fuera (`test/`).
- También tiene lo que no conviene copiar: `YoutubeDL.py` (4.552 líneas, 70 métodos públicos, 140 parámetros en un diccionario), `utils/_utils.py` (5.747 líneas), archivos llamados `common.py`, la CLI en `__init__.py` y estado mutable en `globals.py`.

También se evaluó la ruta `queued_media_downloader/src/queued_media_downloader/`, que repite el nombre.

## Decisión

1. **Un paquete por componente de nuestro dominio,** con su contrato y sus implementaciones: `jobs/`, `job_queue/`, `job_storage/`, `workers/`, `media_extraction/`, `ffmpeg_discovery/`, `diagnostics/`, `command_line/`, `configuration/`. Los casos de uso son módulos con nombre de acción dentro de su componente (`job_queue/enqueue_media.py`).
2. **Reglas de importación en lugar de capas:**
   - un contrato no importa las implementaciones de su paquete;
   - fuera de un paquete solo se importan sus contratos;
   - solo `composition_root.py` importa implementaciones;
   - solo los módulos `yt_dlp_*` importan `yt_dlp`;
   - sin ciclos entre paquetes.
3. **Los job events viven en `jobs/`** y el término *worker event* pasa a ser *job event* ([vocabulario](../design/00-vocabulary.md)). En `workers/` habrían creado un ciclo con `media_extraction/`.
4. **Paquete en la raíz del proyecto, sin `src/`:** `queued-media-downloader/queued_media_downloader/`, con `[tool.uv.build-backend] module-root = ""`. Comprobado: `uv build` genera el wheel con el paquete y `uv sync` lo importa correctamente.
5. **Carpeta del proyecto con guiones** (`queued-media-downloader/`), igual que la distribución; el paquete conserva los guiones bajos. La forma del nombre indica qué es cada nivel.

## Consecuencias

- Al abrir el paquete se ven los componentes del dominio, como en yt-dlp.
- `src/` evitaba importar archivos que no forman parte del paquete instalado. Con `uv sync`, el proyecto se instala en modo editable y el import apunta a la misma carpeta con o sin `src/`; y como el proyecto no se publica en PyPI ([ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md)), el riesgo de un wheel incompleto no aplica.
- Las reglas de importación deben comprobarse automáticamente con un linter de importaciones (pendiente de [ADR-0011](adr-0011-code-conventions.md)).
- `composition_root.py` asume la función de conectar componentes que en yt-dlp cumple `YoutubeDL`, sin acumular su lógica.
