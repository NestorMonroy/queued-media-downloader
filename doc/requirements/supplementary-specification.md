# Especificación complementaria

- **Fase RUP:** Inicio
- **Versión:** 2.0 (2026-11-26; consolidación del modelo de requisitos)
- **Técnica (BABOK v3):** 10.30 Non-Functional Requirements Analysis

Cada requisito tiene un criterio verificable. Los marcados **Propuesto** no están implementados; los que dependen de una medición que falta lo indican como **pendiente** en lugar de inventar un valor.

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
| SUP-U04 | **Propuesto** (UC-11, UC-14): toda espera o pausa de `run` se anuncia con su motivo, su alcance y la hora local estimada de continuación, y el aviso se repite mientras dura ([BR-11](business-rules.md)). Criterio: en una prueba con un reloj falso, el aviso aparece al empezar la espera y una vez por intervalo |
| SUP-U05 | **Propuesto:** el mensaje de cada fallo indica si reintentar puede servir y qué acción lo resuelve ([catálogo de condiciones de fallo](failure-conditions.md)). Criterio: cada `FailureReason` tiene una indicación, comprobada por una prueba que recorre la enumeración |

## Fiabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-R01 | Un cierre inesperado no pierde jobs: al volver a ejecutar `run`, la cola se recupera y las descargas continúan desde lo descargado | [ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md) |
| SUP-R02 | Cancelar o terminar un worker nunca deja procesos de ffmpeg o deno en ejecución, aunque el proceso principal muera | [ADR-0013](../notes/adr-0013-process-tree-terminator-abstraction.md) |
| SUP-R03 | El fallo de un job no detiene el resto de la cola | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-R04 | Un worker que muere de forma inesperada se detecta y se reemplaza; su job queda `FAILED` con `WORKER_CRASHED` | [Parte 2, §3.2](../design/02-flows-persistence-and-operations.md#32-ciclo-de-vida-del-worker) |
| SUP-R05 | Un mismo contenido no se descarga dos veces mientras haya un job activo para su media key | [ADR-0012](../notes/adr-0012-no-download-archive-no-database-triggers.md) |
| SUP-R06 | **Propuesto:** un corte de conectividad no marca ningún job `FAILED` ni gasta intentos. Criterio: UC-11, criterio 1 | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md) A2, [ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md) |
| SUP-R07 | **Propuesto:** una restricción del sitio no marca ningún job `FAILED` ni gasta intentos, y el sitio no recibe más peticiones que las que permite [BR-03](business-rules.md); sin PO Tokens ni evasión. Criterio: UC-11, criterios 1 a 3 | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md) A1, [ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md) |
| SUP-R08 | **Propuesto** (prioridad media): mientras hay jobs en curso, `run` impide que Windows suspenda el equipo, sin impedir que se apague la pantalla; al terminar o detenerse, deja de impedirlo. Criterio: `powercfg /requests` muestra la petición durante `run` y no después (Windows) | [Análisis](requirements-analysis.md), §4.2 |
| SUP-R09 | **Propuesto:** el almacenamiento insuficiente (espacio o cuota) no marca ningún job `FAILED` ni gasta intentos, también cuando aparece tras una comprobación previa correcta; el sistema nunca borra archivos para liberar espacio; las demás condiciones de almacenamiento fallan con la ruta y la acción. Criterio: UC-17, criterios 1 a 5, con una unidad pequeña | [UC-17](use-cases/uc-17-preserve-work-under-storage-failures.md) |
| SUP-R10 | **Propuesto:** un job interrumpido entre el final de la descarga y el registro de `JobCompleted` se completa sin consultar al sitio cuando la evidencia local basta ([BR-23](business-rules.md)), y nunca se completa por la sola existencia de un archivo no vacío ni se apropia de un archivo ajeno. Criterio: UC-06 A11 | [UC-06](use-cases/uc-06-recover-and-resume-queue.md), decisión D-9 |
| SUP-R11 | **Propuesto; hoy hay una divergencia:** los fallos transitorios de una descarga se reintentan como en la línea de comandos de yt-dlp ([BR-07](business-rules.md)). Hoy la librería recibe 0 reintentos HTTP y 0 de fragmentos porque no se pasan los parámetros (R-24). Criterio: una prueba de contrato con un servidor local que falla una vez y luego responde | [Análisis](requirements-analysis.md), §7 |

## Rendimiento y recursos

| ID | Requisito | Origen |
|---|---|---|
| SUP-P01 | Concurrencia por defecto: 1 worker; configurable | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-P02 | La memoria de un worker no crece con el número de entradas de una playlist | [ADR-0009](../notes/adr-0009-playlist-expansion-into-jobs.md) |
| SUP-P03 | El progreso de las descargas no se escribe en la base de datos | [Parte 1, §5](../design/01-architecture.md#5-job-events) |
| SUP-P05 | **Propuesto:** ritmo de peticiones por sitio ([BR-02](business-rules.md)); para YouTube, los valores del preajuste `-t sleep` de yt-dlp; configurable hasta 0 (decisión D-3). Criterio: con un reloj falso, dos jobs de YouTube no empiezan con menos separación que la configurada | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md), [análisis](requirements-analysis.md) |
| SUP-P06 | **Propuesto** (prioridad baja): límite opcional de ancho de banda por descarga (`rate_limit`, sin límite por defecto), con el parámetro `ratelimit` de yt-dlp. Criterio: el parámetro llega a yt-dlp | [Análisis](requirements-analysis.md), §6.1 |
| SUP-P07 | **Pendiente de medición:** espacio en disco que necesita un job además del archivo final (parciales y unión de ffmpeg). Sin este dato no se pueden fijar `storage_margin_mib` ni `storage_estimate_factor` (BR-28) | Medición en la campaña |
| SUP-P04 | **Pendiente de medición.** Presupuesto de memoria (proceso principal + 1 worker, sin contar ffmpeg ni deno): **pendiente**: se fija con la medición en Windows de la campaña T42 (paso 13; trasladada desde E1). Referencia de la medición en Linux: ~38 MB por proceso con yt-dlp cargado | Medición del análisis (`scripts/measure_footprint.py`, espacio de trabajo `yt-dlp-gui-clone`) |

## Mantenibilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-S01 | Actualizar yt-dlp es un procedimiento documentado: cambiar la versión fijada, ejecutar las pruebas de contrato, publicar | [ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md), [procedimiento](../process/yt-dlp-update-procedure.md) |
| SUP-S02 | Todo el código cumple las reglas de importación (`lint-imports`), el formato y el linter (Ruff) y la verificación de tipos estricta (mypy) | [ADR-0017](../notes/adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S03 | Identificadores en inglés según el vocabulario; docstrings y comentarios en español | [ADR-0011](../notes/adr-0011-code-conventions.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S04 | Las reglas de la cola (`jobs/`, `job_queue/`) se prueban sin yt-dlp, sin SQLite y sin procesos | [Parte 1, §1](../design/01-architecture.md#1-principios-de-diseño) |

## Seguridad

| ID | Requisito | Origen |
|---|---|---|
| SUP-SEC01 | **Propuesto** (condicionado a D-1 y D-7): ningún valor de una credencial configurada (cookies, contraseña de un proxy) aparece en el log, en `diagnose`, en un informe (UC-16) ni en la evidencia de validación. Criterio: prueba con valores trampa que busca el valor en cada salida | VoiceStudio (limpieza del informe de diagnóstico); [análisis](requirements-analysis.md), §6 |
| SUP-SEC02 | **Propuesto:** el informe de diagnóstico y la evidencia nunca incluyen archivos multimedia | UC-16; campaña T42 (el empaquetado manual sin videos) |
| SUP-SEC03 | **Propuesto** (condicionado a D-1 y D-7): un archivo que guarde credenciales (cookies, proxy con contraseña) se crea ya restringido al usuario actual, sin un intervalo en que otros puedan leerlo. Criterio: prueba que crea el archivo y comprueba sus permisos (en Windows, su ACL) | VoiceBlueprintPro (`core/user_env.py`, creación con permisos 0600) |

## Observabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-O01 | El log se escribe en la carpeta de estado y rota (5 MB, 3 copias). **Vigente** | `command_line/log_file.py` |
| SUP-O02 | `diagnose` comprueba ffmpeg, ffprobe, yt-dlp, deno y la base de datos, y termina con código distinto de `0` si algo falla. **Vigente** | UC-01 |
| SUP-O03 | **Propuesto:** el diagnóstico operativo (UC-16) y la evidencia de validación (VUC-07) comparten el mismo mecanismo de recogida y de limpieza | [Análisis](requirements-analysis.md), §6 |

## Validación y reproducibilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-V01 | **Parcial** (hoy, las de los jobs y la cola; faltan las condiciones externas): toda condición de [failure-conditions.md](failure-conditions.md) que no dependa de un sitio real se prueba con pytest, fixtures y el servidor local, en cualquier sistema | [Modelo de validación](../process/validation-use-case-model.md) |
| SUP-V02 | **Propuesto:** quien ejecuta una prueba no emite su veredicto ([VBR-04](business-rules.md)) | VoiceStudio (arnés de sondeo) |
| SUP-V03 | **Propuesto:** cada mensaje real de un sitio que el producto reconoce tiene una prueba de regresión con el texto literal, incluidas sus variantes tipográficas | VoiceStudio; BR-01 |

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
