# Visión

- **Proyecto:** queued-media-downloader
- **Fase RUP:** Inicio
- **Versión:** 1.4 (2026-11-26; ampliaciones propuestas del descubrimiento funcional, instrucción 2.5.0, pendientes de aprobación). 1.3 (2026-11-26; **orientación multiplataforma**, instrucción 2.3.0). 1.2: alcance de 26 casos de uso aceptado por el Responsable. 1.1: alcance revisado en la reconciliación de exclusiones. 1.0: 2026-11-23, borrador para revisión

---

## 1. Problema

| | |
|---|---|
| **El problema de** | descargar contenidos de sitios de video y audio de forma fiable, sobre todo playlists y canales completos |
| **afecta a** | usuarios de Windows, incluidos los que tienen equipos y conexiones modestos |
| **cuyo impacto es** | descargas que se pierden al cerrar la aplicación o fallar la red, procesos que quedan colgados, configuración manual de ffmpeg y dependencias, y uso de una herramienta de línea de comandos con cientos de opciones |
| **una solución exitosa** | administra de manera persistente, configurable, segura, recuperable y eficiente la obtención de contenidos multimedia y de su información complementaria, mediante una cola de trabajos que admite operaciones individuales, por lotes y desatendidas, y se instala con un solo flujo reproducible |

## 2. Posicionamiento

**Formulación del producto:** un motor reutilizable para administrar de forma persistente, configurable, segura, recuperable y eficiente la obtención de contenidos multimedia y su información complementaria. Sus contratos funcionales no dependen de la interfaz de usuario y está preparado para evolucionar hacia aplicaciones en Windows, Android e iOS, respetando las capacidades y restricciones de cada plataforma ([ADR-0032](../notes/adr-0032-reusable-engine-and-platform-capabilities.md)).

| Dimensión | Disposición |
|---|---|
| Alcance funcional | Los 26 casos de uso aceptados, un único modelo para todas las interfaces |
| Interfaz inicial | Línea de comandos |
| Plataforma inicial | Windows x64: la primera que se implementa y se acepta, no una restricción permanente |
| Alcance de implementación inmediato | La CLI de Windows (E3, cuando se autorice) |
| Evolución futura | Aplicación gráfica para Windows y aplicaciones para Android e iOS; no autorizadas todavía |
| Restricciones de la evolución | Las capacidades de cada plataforma: en iOS no hay procesos y la ejecución en segundo plano no está garantizada; en Android está limitada (R-31; [diseño, Parte 3, §7](../design/03-target-architecture-and-evolution.md#7-cualificación-multiplataforma)) |
| Validación integral en Windows | Después de implementar el alcance aceptado |

| | |
|---|---|
| **Para** | usuarios de Windows que descargan contenidos con frecuencia |
| **que** | necesitan descargar muchos contenidos sin vigilar cada descarga |
| **queued-media-downloader es** | un descargador con cola persistente construido sobre la librería yt-dlp |
| **que** | encola, ejecuta, cancela, reintenta y reanuda descargas, con ffmpeg incluido |
| **a diferencia de** | yt-dlp por línea de comandos (sin cola persistente ni cancelación por elemento) y de interfaces gráficas como yt-dlp-gui (que delegan en ejecutables externos que el usuario debe obtener y colocar) |
| **nuestro producto** | usa yt-dlp como librería, con un motor cuyas reglas y contratos reutilizarán sin duplicarse las interfaces futuras (gráfica, Android, iOS) |

## 3. Interesados

| Interesado | Interés | Responsabilidad |
|---|---|---|
| Usuario final | Descargar sin perder trabajo ni configurar herramientas | Instalar con uv y usar la línea de comandos |
| Autor y mantenedor | Diseño limpio, modular y documentado; actualizar yt-dlp y ffmpeg de forma controlada | Desarrollar, decidir (ADR) y publicar |

## 4. Capacidades del producto

Formulación del alcance: **administrar de manera persistente, configurable, segura, recuperable y eficiente la obtención de contenidos multimedia y de su información complementaria, mediante una cola de trabajos que admite operaciones individuales, por lotes y desatendidas.** El Responsable aceptó el alcance de los 26 casos de uso de la tabla (2026-11-26). La aceptación no implica que estén implementados: el estado de cada uno está en el [modelo](use-case-model.md#4-casos-de-uso), y las soluciones técnicas, en el [análisis, §9](requirements-analysis.md#9-decisiones).

| Necesidad | Casos de uso |
|---|---|
| Obtención multimedia | UC-02 (encolar, con preajustes, capítulos, secciones, SponsorBlock, contenedor y conversión), UC-03 (descargar), UC-04 (playlists y canales), UC-15 (consultar y buscar antes de encolar) |
| Información complementaria | UC-02 A7 y UC-03 A16 (junto con el contenido); UC-24 (sin descargar el contenido) |
| Administración de trabajos | UC-05 (cancelar), UC-07 (reintentar), UC-08 y UC-09 (consultar), UC-10 (purgar registros) |
| Administración de resultados | UC-25 (consultar, localizar y eliminar resultados propios) |
| Recuperación e integridad | UC-06 (recuperar y reanudar), UC-26 (verificar resultados), UC-23 (respaldar y restaurar) |
| Configuración | UC-20 (configuración), UC-18 (perfiles de descarga) |
| Operación desatendida | UC-11 (sitio y conectividad), UC-17 (almacenamiento), UC-14 (pausa, continuación y detención), UC-21 (programación), UC-28 (avisos); directos y programados (UC-03 E1) |
| Acceso autorizado | UC-19 (perfiles de acceso: archivos de cookies del User, proxy en modo sistema, directo o explícito) |
| Administración de recursos | SUP-P01 a SUP-P09 (workers, ancho de banda, fragmentos, memoria, espacio) |
| Automatización e interoperabilidad | SUP-I01 (salida estructurada de todos los comandos; mecanismo adicional según D-17) |
| Diagnóstico | UC-01 (instalar y verificar), UC-16 (informe de diagnóstico) |
| Portabilidad de la información | UC-22 (exportar e importar), UC-23 (respaldo), UC-20 A5 (configuración) |
| Dependencias | UC-01 y UC-27 (administración controlada y reversible) |

**Ampliaciones propuestas, pendientes de aprobación** (instrucción 2.5.0, [análisis de requisitos, §15](requirements-analysis.md#15-descubrimiento-funcional-250)): no cambian la formulación del alcance y no lo reducen.
- **Candidatos:** modificar jobs pendientes (UC-29), suscripciones a fuentes y obtención de contenido nuevo (UC-30, UC-31) y actualización de la aplicación (UC-32).
- **Ampliaciones de casos aceptados:** solicitudes desde otras aplicaciones y portapapeles (UC-02), pausa y orden de jobs y acción al terminar la cola (UC-14), usuario y contraseña del sitio (UC-19), selecciones (UC-05, UC-10), perfiles por URL e idioma (UC-18), modo privado y borrado por categoría (UC-20), programación por job (UC-21), abrir, compartir y exportar resultados (UC-25).
- **Sin decidir:** el alcance de consumo (reproducción, catálogos, transcripción, IA; D-23) y el modelo comercial y los canales en tiendas (D-24). La visión no se amplía a plataforma social, tienda, servicio de streaming ni sistema comercial sin esas decisiones.

## 5. Restricciones

- **Plataforma:** Windows 10/11 x64 en esta versión ([ADR-0004](../notes/adr-0004-windows-x64-target-platform.md); primera plataforma, no restricción permanente según [ADR-0032](../notes/adr-0032-reusable-engine-and-platform-capabilities.md)).
- **Dependencias fijadas:** yt-dlp 2026.11.23 ([ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md)) y ffmpeg 9.0 LGPL incluido ([ADR-0018](../notes/adr-0018-ffmpeg-build-selection.md)).
- **Instalación:** `git clone` → `uv sync` → `uv run`; sin Python preinstalado ([ADR-0003](../notes/adr-0003-packaging-with-uv-and-pyproject.md)).
- **Licencia:** The Unlicense, con la excepción LGPL de `vendor/ffmpeg/` ([ADR-0007](../notes/adr-0007-project-license-unlicense.md)).
- **Recursos mínimos:** 1 worker por defecto ([ADR-0008](../notes/adr-0008-process-based-worker-pool.md)).

## 6. Fuera de alcance

Cada exclusión está cualificada en el [análisis, §12](requirements-analysis.md#12-reconciliación-de-exclusiones), que separa la necesidad de la solución. Excluir una tecnología o una interfaz no excluye la necesidad que resolvería.

**Fuera del dominio:** síntesis y clonación de voz; transcripción o traducción con inteligencia artificial; edición multimedia general; administración general de cuentas; recortes de voz para otros productos.

**Restricciones vigentes:**
- PO Tokens y cualquier mecanismo para evadir los controles, bloqueos o restricciones geográficas de un sitio (decisión del Responsable, 2026-11-26), incluidos cambiar de cliente de YouTube y rotar proxies o agentes de usuario;
- ejecución de comandos o scripts arbitrarios del sistema.

**Tecnologías excluidas** (su necesidad está cubierta por otro destino):
- aria2c (SUP-P09);
- navegadores automatizados como Playwright (UC-19);
- `--download-archive` (BR-32, ADR-0012).

**Interfaces diferidas:** interfaz gráfica de Windows, aplicaciones de Android e iOS ([ADR-0001](../notes/adr-0001-project-scope.md), aclarado por [ADR-0032](../notes/adr-0032-reusable-engine-and-platform-capabilities.md)) y temas visuales; servidor MCP o API HTTP (D-17). El motor ya expone sus operaciones para que se reutilicen sin duplicar la lógica.

**Condiciones técnicas pendientes** (no excluyen el objetivo): recodificar a H.264 o HEVC (patentes, R-29); leer las cookies del navegador (UC-19 A10); probar versiones no cualificadas de yt-dlp (UC-27 A2).

**Decisiones de soporte y distribución:** Windows ARM64 y otras plataformas de escritorio (SUP-C06); publicación en PyPI (SUP-C07). Android e iOS no son exclusiones: son evolución prevista, con su viabilidad por cualificar.

## 7. Criterios de éxito

- Un usuario sin Python instalado deja el entorno listo y verificado siguiendo solo el README.
- Cerrar la aplicación a mitad de una descarga y volver a ejecutar `run` continúa desde lo descargado.
- Cancelar un job nunca deja procesos de ffmpeg o deno en ejecución.
- Una playlist grande se procesa sin que la memoria crezca con el número de entradas.
