# ADR-0015: Nombre del proyecto y del paquete

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** la carpeta del proyecto se llama `queued-media-downloader/` (con guiones) desde [ADR-0016](adr-0016-component-packages-and-flat-layout.md).
- **Ajusta:** el nombre de trabajo usado en ADR-0001 a ADR-0014

## Contexto

El paquete se iba a llamar `yt_dlp_gui_clone`, heredado del nombre de trabajo del proyecto. Evaluado con los [principios de nombres](../reference/naming-principles/clean-code-naming-principles.md):
- **#2 Desinformación:** dice *gui*, y el alcance es explícitamente sin GUI ([ADR-0001](adr-0001-project-scope.md)).
- **#9 La arquitectura revela intención:** *clone* indica de dónde vino la idea, no qué hace el sistema.
- **Prefijo `yt_dlp_`:** sugiere que forma parte de yt-dlp, que usa ese espacio de nombres para lo suyo (por ejemplo, `yt_dlp_plugins`).

## Opciones consideradas

1. **`queued_media_downloader`:** describe el sistema completo: descarga contenidos mediante una cola.
2. **`media_download_queue`:** casi repite el paquete interior `download_queue/` (#3, distinciones sin sentido).
3. **`media_fetcher`:** usa *fetch*, verbo prohibido por el [vocabulario](../design/00-vocabulary.md), y no menciona la cola.

## Decisión

| Elemento | Nombre |
|---|---|
| Paquete de Python | `queued_media_downloader` |
| Distribución (`[project] name`) y comando | `queued-media-downloader` |
| Carpeta del proyecto | `queued_media_downloader/` |
| Prefijo de variables de entorno | `QUEUED_MEDIA_DOWNLOADER_` |
| Carpeta de descargas por defecto | `%USERPROFILE%\Downloads\queued-media-downloader` |

La distribución usa guiones porque es la forma normalizada de los nombres de paquetes en PyPI; el paquete usa guiones bajos porque es un identificador de Python. Son el mismo nombre en sus dos formas, sin traducción mental (#7).

## Consecuencias

- Si llega una GUI, será un plugin de este paquete y el nombre seguirá siendo cierto.
- El análisis previo queda en el espacio de trabajo `yt-dlp-gui-clone/`, que conserva su nombre: describe lo que fue (el análisis de yt-dlp), no el producto.
- Los ADR anteriores no se reescriben; esta tabla indica cómo leer el nombre de trabajo que aparezca en ellos.
