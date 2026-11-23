# ADR-0017: API pública por componente, ensamblaje en el programa y grafo comprobado

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Completa:** las reglas de importación de [ADR-0016](adr-0016-component-packages-and-flat-layout.md)
- **Resuelve en parte:** el pendiente de herramientas de [ADR-0011](adr-0011-code-conventions.md) (linter de importaciones)

## Contexto

Se analizó la estructura de FFmpeg (rama principal, 2026-11-22):
- **Librerías separadas de los programas:** la funcionalidad está en `libavutil`, `libavcodec`, `libavformat`, `libavfilter`, `libavdevice`, `libswscale` y `libswresample`; `fftools/` contiene los programas (`ffmpeg`, `ffprobe`, `ffplay`), y cada uno declara qué librerías usa (`ffprobe_deps="avcodec avformat"`).
- **Dependencias declaradas y comprobadas por la compilación**, sin ciclos (`avformat_deps="avcodec avutil"`).
- **API pública mínima:** `libavformat` tiene 748 archivos y 4 cabeceras públicas; `libavcodec`, 2.788 y 25.
- **Contrato e implementaciones con registro explícito:** `FFCodec` (estructura con punteros a funciones) y 883 códecs registrados en `allcodecs.c`.

Coincide en lo esencial con ADR-0016 (componentes, contratos, registro explícito, sin ciclos). La diferencia es de escala: FFmpeg distribuye librerías por separado porque otros programas enlazan solo las que necesitan. No es nuestro caso: un solo producto.

También se evaluó sustituir `queued-media-downloader/queued_media_downloader/` por `queued_media_downloader/src/`. Probado con `uv_build`: no admite que la carpeta y el nombre del import difieran; los componentes sueltos en `src/` se instalarían con nombres de primer nivel que ya existen en PyPI (`jobs`, `workers`, `configuration`, `diagnostics`, `command-line`); y un paquete llamado `src` no revela nada (#1, #9). Se descarta.

## Decisión

Se adoptan tres ideas de FFmpeg:

**A. El ensamblaje pertenece al programa.** `composition_root.py` pasa a `command_line/composition_root.py`. Una GUI futura sería un paquete hermano de `command_line/` con su propio ensamblaje.

**B. API pública por componente.** El `__init__.py` de cada componente exporta sus contratos y tipos, nunca implementaciones. Fuera del componente solo se importa desde ese `__init__.py`. Solo `command_line/composition_root.py` puede importar módulos internos de otros componentes.

**C. Grafo de dependencias declarado y comprobado** con `import-linter` en `pyproject.toml`:
- un contrato `layers` con los niveles de componentes (sin ciclos);
- un contrato `protected` **por componente** (proteger varios en uno solo autoriza a cada paquete a usar el interior de los demás, como mostró la prueba);
- un contrato `forbidden` para que solo `media_extraction/` importe `yt_dlp` (requiere `include_external_packages = true`).

Validado con `import-linter` 2.17 y el wheel de yt-dlp 2026.10.26 sobre un paquete de prueba con esta estructura: la estructura correcta cumple los tres contratos, y se detectan un ciclo desde `jobs/`, un import de `job_storage.sqlite_job_store` desde `job_queue/`, un import de `media_extraction.yt_dlp_media_source` desde `workers/` y un `import yt_dlp` desde `workers/`.

No se adoptan: librerías distribuidas por separado (YAGNI), prefijos como `libav*` o `ff_` (en Python los paquetes ya son espacios de nombres; serían codificaciones, #6), ni carpetas de miles de archivos sin subdividir.

## Consecuencias

- La regla "fuera de un paquete solo se importan sus contratos" deja de depender de la memoria de cada persona: la comprueba `lint-imports`.
- `import-linter` se añade a `[dependency-groups] dev` y se ejecuta junto con las pruebas.
- El vocabulario incorpora *public API* y *composition root* ([vocabulario](../design/00-vocabulary.md)).
- Que `media_source.py` no importe `yt_dlp` se revisa en código: los patrones de `import-linter` trabajan por segmentos completos del nombre y el contrato autoriza a todo `media_extraction/`.
