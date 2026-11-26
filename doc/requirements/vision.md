# Visión

- **Proyecto:** queued-media-downloader
- **Fase RUP:** Inicio
- **Versión:** 1.0 (borrador para revisión)
- **Fecha:** 2026-11-23

---

## 1. Problema

| | |
|---|---|
| **El problema de** | descargar contenidos de sitios de video y audio de forma fiable, sobre todo playlists y canales completos |
| **afecta a** | usuarios de Windows, incluidos los que tienen equipos y conexiones modestos |
| **cuyo impacto es** | descargas que se pierden al cerrar la aplicación o fallar la red, procesos que quedan colgados, configuración manual de ffmpeg y dependencias, y uso de una herramienta de línea de comandos con cientos de opciones |
| **una solución exitosa** | gestiona una cola persistente que sobrevive a cierres, reanuda lo descargado, permite cancelar en cualquier momento y se instala con un solo flujo reproducible |

## 2. Posicionamiento

| | |
|---|---|
| **Para** | usuarios de Windows que descargan contenidos con frecuencia |
| **que** | necesitan descargar muchos contenidos sin vigilar cada descarga |
| **queued-media-downloader es** | un descargador con cola persistente construido sobre la librería yt-dlp |
| **que** | encola, ejecuta, cancela, reintenta y reanuda descargas, con ffmpeg incluido |
| **a diferencia de** | yt-dlp por línea de comandos (sin cola persistente ni cancelación por elemento) y de interfaces gráficas como yt-dlp-gui (que delegan en ejecutables externos que el usuario debe obtener y colocar) |
| **nuestro producto** | usa yt-dlp como librería, con un motor diseñado para que una interfaz gráfica futura lo reutilice sin cambios |

## 3. Interesados

| Interesado | Interés | Responsabilidad |
|---|---|---|
| Usuario final | Descargar sin perder trabajo ni configurar herramientas | Instalar con uv y usar la línea de comandos |
| Autor y mantenedor | Diseño limpio, modular y documentado; actualizar yt-dlp y ffmpeg de forma controlada | Desarrollar, decidir (ADR) y publicar |

## 4. Capacidades del producto

| Capacidad | Caso de uso |
|---|---|
| Instalar con un flujo reproducible y verificar el entorno | [UC-01](use-cases/uc-01-install-and-verify-environment.md) |
| Encolar contenidos (videos, playlists, canales) | [UC-02](use-cases/uc-02-enqueue-media.md) |
| Descargar contenidos con progreso | [UC-03](use-cases/uc-03-download-single-media.md) |
| Expandir playlists y canales en descargas individuales | [UC-04](use-cases/uc-04-expand-playlist.md) |
| Cancelar descargas en cualquier momento | [UC-05](use-cases/uc-05-cancel-job.md) |
| Recuperar la cola y reanudar descargas tras un cierre | [UC-06](use-cases/uc-06-recover-and-resume-queue.md) |
| Reintentar, listar, ver y purgar jobs | [Modelo de casos de uso](use-case-model.md) |
| Preservar los jobs ante una restricción del sitio, un corte de conectividad o falta de espacio (propuesto) | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md) |
| Pausar, continuar o detener de forma ordenada la cola desde cualquier terminal (propuesto) | [UC-14](use-cases/uc-14-control-queue-execution.md) |
| Consultar formatos y entradas de una URL antes de encolarla (propuesto) | [UC-15](use-cases/uc-15-inspect-media-before-enqueueing.md) |
| Preparar un informe de diagnóstico para reportar un problema (propuesto) | [UC-16](use-cases/uc-16-prepare-a-diagnostic-report.md) |

## 5. Restricciones

- **Plataforma:** Windows 10/11 x64 ([ADR-0004](../notes/adr-0004-windows-x64-target-platform.md)).
- **Dependencias fijadas:** yt-dlp 2026.11.23 ([ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md)) y ffmpeg 9.0 LGPL incluido ([ADR-0018](../notes/adr-0018-ffmpeg-build-selection.md)).
- **Instalación:** `git clone` → `uv sync` → `uv run`; sin Python preinstalado ([ADR-0003](../notes/adr-0003-packaging-with-uv-and-pyproject.md)).
- **Licencia:** The Unlicense, con la excepción LGPL de `vendor/ffmpeg/` ([ADR-0007](../notes/adr-0007-project-license-unlicense.md)).
- **Recursos mínimos:** 1 worker por defecto ([ADR-0008](../notes/adr-0008-process-based-worker-pool.md)).

## 6. Fuera de alcance

- Interfaz gráfica (alcance inicial, [ADR-0001](../notes/adr-0001-project-scope.md)).
- Otras plataformas, incluido Windows ARM64.
- Publicación en PyPI.
- Recodificar video (la build LGPL no incluye codificadores H.264/H.265).
- PO Tokens y cualquier mecanismo para evadir los controles de un sitio (decisión del Responsable, 2026-11-26). Cookies y proxy, solo como acceso legítimo: decisiones D-1 y D-7 del [análisis](requirements-analysis.md#9-decisiones-pendientes).
- Edición del contenido (SponsorBlock, partir por capítulos), comandos personalizados de yt-dlp y descargas con aria2c: [análisis, §6.3](requirements-analysis.md#63-exclusiones).

## 7. Criterios de éxito

- Un usuario sin Python instalado deja el entorno listo y verificado siguiendo solo el README.
- Cerrar la aplicación a mitad de una descarga y volver a ejecutar `run` continúa desde lo descargado.
- Cancelar un job nunca deja procesos de ffmpeg o deno en ejecución.
- Una playlist grande se procesa sin que la memoria crezca con el número de entradas.
