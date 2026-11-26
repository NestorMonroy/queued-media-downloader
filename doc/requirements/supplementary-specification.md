# Especificación complementaria

- **Fase RUP:** Inicio
- **Versión:** 3.3 (2026-11-26; instrucción 2.6.0: SUP-I06, SUP-D02, SUP-C11 a SUP-C13 y SUP-U06 aceptados; SUP-C13 aplica solo si se elige Google Play; nuevos SUP-SEC07 y SUP-D03). 3.2 (2026-11-26; propuestos SUP-I06, SUP-D02, SUP-C11 a SUP-C13 y SUP-U06, pendientes de aprobación). 3.1 (2026-11-26; Analysis and Design: independencia de la interfaz, contratos públicos versionados, portabilidad de identidades, capacidades por ambiente, compatibilidad de instalaciones). 3.0 (2026-11-26; alcance aceptado; seguridad de entradas y rutas, retención, contrato programático). 2.1 (2026-11-26; reconciliación de exclusiones: interoperabilidad, compatibilidad multimedia, portabilidad, credenciales y respaldo). 2.0: consolidación del modelo de requisitos
- **Técnica (BABOK v3):** 10.30 Non-Functional Requirements Analysis

Cada requisito tiene un criterio verificable. El alcance está aceptado por el Responsable (2026-11-26). **Aceptado, sin implementar** indica que el requisito forma parte del producto y todavía no existe en el código. Los que dependen de una medición que falta lo indican como **pendiente**, con el método de cualificación, en lugar de inventar un valor.

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
| SUP-U04 | **Aceptado, sin implementar** (UC-11, UC-14): toda espera o pausa de `run` se anuncia con su motivo, su alcance y la hora local estimada de continuación, y el aviso se repite mientras dura ([BR-11](business-rules.md)). Criterio: en una prueba con un reloj falso, el aviso aparece al empezar la espera y una vez por intervalo |
| SUP-U05 | **Aceptado, sin implementar:** el mensaje de cada fallo indica si reintentar puede servir y qué acción lo resuelve ([catálogo de condiciones de fallo](failure-conditions.md)). Criterio: cada `FailureReason` tiene una indicación, comprobada por una prueba que recorre la enumeración |
| SUP-U06 | **Aceptado (2.6.0), sin implementar:** el idioma de la interfaz, el idioma y el país con que se consulta un sitio, el idioma de la pista de audio y el de los subtítulos son preferencias distintas, con valores y efectos documentados; solo las que cambian el resultado pedido forman parte de su identidad. Criterio: tabla de preferencias con su efecto y prueba de que cambiar el idioma de la interfaz no cambia la identidad de una petición | UC-18 A9; vocabulario; [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |

## Fiabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-R01 | Un cierre inesperado no pierde jobs: al volver a ejecutar `run`, la cola se recupera y las descargas continúan desde lo descargado | [ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md) |
| SUP-R02 | Cancelar o terminar un worker nunca deja procesos de ffmpeg o deno en ejecución, aunque el proceso principal muera | [ADR-0013](../notes/adr-0013-process-tree-terminator-abstraction.md) |
| SUP-R03 | El fallo de un job no detiene el resto de la cola | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-R04 | Un worker que muere de forma inesperada se detecta y se reemplaza; su job queda `FAILED` con `WORKER_CRASHED` | [Parte 2, §3.2](../design/02-flows-persistence-and-operations.md#32-ciclo-de-vida-del-worker) |
| SUP-R05 | Un mismo contenido no se descarga dos veces mientras haya un job activo para su media key | [ADR-0012](../notes/adr-0012-no-download-archive-no-database-triggers.md) |
| SUP-R06 | **Aceptado, sin implementar:** un corte de conectividad no marca ningún job `FAILED` ni gasta intentos. Criterio: UC-11, criterio 1 | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md) A2, [ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md) |
| SUP-R07 | **Aceptado, sin implementar:** una restricción del sitio no marca ningún job `FAILED` ni gasta intentos, y el sitio no recibe más peticiones que las que permite [BR-03](business-rules.md); sin PO Tokens ni evasión. Criterio: UC-11, criterios 1 a 3 | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md) A1, [ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md) |
| SUP-R08 | **Aceptado, sin implementar** (prioridad media): mientras hay jobs en curso, `run` impide que Windows suspenda el equipo, sin impedir que se apague la pantalla; al terminar o detenerse, deja de impedirlo. Criterio: `powercfg /requests` muestra la petición durante `run` y no después (Windows) | [Análisis](requirements-analysis.md), §4.2 |
| SUP-R09 | **Aceptado, sin implementar:** el almacenamiento insuficiente (espacio o cuota) no marca ningún job `FAILED` ni gasta intentos, también cuando aparece tras una comprobación previa correcta; el sistema nunca borra archivos para liberar espacio; las demás condiciones de almacenamiento fallan con la ruta y la acción. Criterio: UC-17, criterios 1 a 5, con una unidad pequeña | [UC-17](use-cases/uc-17-preserve-work-under-storage-failures.md) |
| SUP-R10 | **Aceptado, sin implementar:** un job interrumpido entre el final de la descarga y el registro de `JobCompleted` se completa sin consultar al sitio cuando la evidencia local basta ([BR-23](business-rules.md)), y nunca se completa por la sola existencia de un archivo no vacío ni se apropia de un archivo ajeno. Criterio: UC-06 A11 | [UC-06](use-cases/uc-06-recover-and-resume-queue.md), decisión D-9 |
| SUP-R12 | **Aceptado, sin implementar:** un respaldo hecho con `run` activo es coherente y pasa la comprobación de integridad de SQLite (UC-23) | UC-23 |
| SUP-R11 | **Aceptado; hoy divergente (R-24):** los fallos transitorios de una descarga se reintentan como en la línea de comandos de yt-dlp ([BR-07](business-rules.md)). Hoy la librería recibe 0 reintentos HTTP y 0 de fragmentos porque no se pasan los parámetros (R-24). Criterio: una prueba de contrato con un servidor local que falla una vez y luego responde | [Análisis](requirements-analysis.md), §7 |

## Rendimiento y recursos

| ID | Requisito | Origen |
|---|---|---|
| SUP-P01 | Concurrencia por defecto: 1 worker; configurable | [ADR-0008](../notes/adr-0008-process-based-worker-pool.md) |
| SUP-P02 | La memoria de un worker no crece con el número de entradas de una playlist | [ADR-0009](../notes/adr-0009-playlist-expansion-into-jobs.md) |
| SUP-P03 | El progreso de las descargas no se escribe en la base de datos | [Parte 1, §5](../design/01-architecture.md#5-job-events) |
| SUP-P05 | **Aceptado, sin implementar:** ritmo de peticiones por sitio ([BR-02](business-rules.md)); para YouTube, los valores del preajuste `-t sleep` de yt-dlp; configurable hasta 0 (decisión D-3). Criterio: con un reloj falso, dos jobs de YouTube no empiezan con menos separación que la configurada | [UC-11](use-cases/uc-11-preserve-jobs-under-external-conditions.md), [análisis](requirements-analysis.md) |
| SUP-P06 | **Aceptado, sin implementar:** límite opcional de ancho de banda por descarga (`rate_limit`, sin límite por defecto), con el parámetro `ratelimit` de yt-dlp; un límite global entre workers es la decisión D-20. Criterio: el parámetro llega a yt-dlp | [Análisis](requirements-analysis.md), §6.1 |
| SUP-P07 | **Pendiente de medición:** espacio en disco que necesita un job además del archivo final (parciales y unión de ffmpeg). Sin este dato no se pueden fijar `storage_margin_mib` ni `storage_estimate_factor` (BR-28) | Medición en la campaña |
| SUP-P08 | **Pendiente de medición:** con N resultados por job (capítulos, secciones, complementarios) y con colas de larga duración, el espacio y la memoria por job dependen del número de resultados. SUP-P04 y SUP-P07 se miden también con un job de capítulos y con una playlist larga | Análisis, §13.1 |
| SUP-P09 | **Aceptado, sin implementar:** el número de fragmentos concurrentes por descarga es configurable (`concurrent_fragments`, 1 por omisión) y se usa con el valor de yt-dlp, sin un descargador propio. Criterio: el parámetro llega a yt-dlp; la concurrencia total es `worker_count` × `concurrent_fragments` | yt-dlp `concurrent_fragment_downloads`; Seal; [análisis, §12](requirements-analysis.md#12-reconciliación-de-exclusiones) |
| SUP-P04 | **Pendiente de medición.** Presupuesto de memoria (proceso principal + 1 worker, sin contar ffmpeg ni deno): **pendiente**: se fija con la medición en Windows de la campaña T42 (paso 13; trasladada desde E1). Referencia de la medición en Linux: ~38 MB por proceso con yt-dlp cargado | Medición del análisis (`scripts/measure_footprint.py`, espacio de trabajo `yt-dlp-gui-clone`) |

## Mantenibilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-S01 | Actualizar yt-dlp es un procedimiento documentado: cambiar la versión fijada, ejecutar las pruebas de contrato, publicar | [ADR-0002](../notes/adr-0002-pinned-yt-dlp-version.md), [procedimiento](../process/yt-dlp-update-procedure.md) |
| SUP-S02 | Todo el código cumple las reglas de importación (`lint-imports`), el formato y el linter (Ruff) y la verificación de tipos estricta (mypy) | [ADR-0017](../notes/adr-0017-ffmpeg-inspired-public-api-and-dependency-graph.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S03 | Identificadores en inglés según el vocabulario; docstrings y comentarios en español | [ADR-0011](../notes/adr-0011-code-conventions.md), [ADR-0019](../notes/adr-0019-code-quality-tools.md) |
| SUP-S04 | Las reglas de la cola (`jobs/`, `job_queue/`) se prueban sin yt-dlp, sin SQLite y sin procesos | [Parte 1, §1](../design/01-architecture.md#1-principios-de-diseño) |
| SUP-S05 | **Aceptado; vigente:** las reglas, los casos de uso y los componentes del motor no dependen de la interfaz: solo `command_line` importa `argparse`, y `jobs` no importa mecanismos que varían por ambiente (`sqlite3`, `subprocess`, `multiprocessing`, `ctypes`, `signal`, `yt_dlp`). Criterio: los contratos AR-02 y AR-04 de `lint-imports` | ADR-0032; [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §9.1 |
| SUP-S06 | **Aceptado, sin implementar:** el ensamblaje del producto (abrir la instalación, componer las implementaciones, recuperar y ejecutar la sesión) existe una sola vez y ninguna interfaz lo duplica. Criterio: un programa cliente de prueba ejecuta una sesión completa sin `argparse` ni stdout (AAC-02); `command_line` no importa `sqlite3` (AR-03) | ADR-0032; [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §4.2 |

## Seguridad

| ID | Requisito | Origen |
|---|---|---|
| SUP-SEC01 | **Aceptado, sin implementar:** ningún valor de una credencial configurada (cookies, contraseña de un proxy, también dentro de la URL del proxy) aparece en el log, la base de datos (`failure_message`), `diagnose`, la salida JSON, un aviso, un informe (UC-16), una exportación, un respaldo ni la evidencia de validación. El enmascarado se hace en el origen, antes de que el dato llegue a una autoridad de registro o persistencia (D-7), no solo al presentarlo. Criterio: prueba con valores trampa que busca el valor en cada salida | VoiceStudio (limpieza del informe de diagnóstico); [análisis](requirements-analysis.md), §6 |
| SUP-SEC02 | **Aceptado, sin implementar:** el informe de diagnóstico y la evidencia nunca incluyen archivos multimedia | UC-16; campaña T42 (el empaquetado manual sin videos) |
| SUP-SEC04 | **Aceptado, sin implementar** (condicionado a D-1 y D-7): ninguna copia temporal de credenciales sobrevive al job que la usó ni a un arranque de `run` (BR-35). Criterio: prueba con un cierre a mitad del job | UC-19 |
| SUP-SEC05 | **Aceptado, sin implementar:** los documentos importados (UC-22) y los respaldos (UC-23) se tratan como entrada no confiable: se validan su esquema, su versión y sus rutas antes de escribir nada, y nunca conceden la propiedad de un archivo (BR-36). Criterio: pruebas con documentos y respaldos manipulados (rutas fuera del destino, versiones desconocidas, campos de más) | §13.15 del análisis |
| SUP-SEC06 | **Aceptado; vigente en parte:** toda ruta final se resuelve dentro de la carpeta de descargas configurada, sin escribir fuera aunque el título o la plantilla contengan `..` o enlaces. Hoy `canonical_stem_path` normaliza la ruta (ADR-0030), pero no hay una prueba de escritura fuera del destino. Criterio: prueba con títulos y plantillas maliciosos | §13.15 del análisis |
| SUP-SEC07 | **Aceptado (2.6.0), sin implementar:** una URL puede llevar secretos (tokens, firmas, claves de acceso, usuario y contraseña). El producto distingue cuatro representaciones de una misma URL: **operativa** (la completa, que se usa para obtener el contenido y que nunca se recorta si un parámetro es necesario), **pública** (la que se muestra en la interfaz y en las listas, con los secretos reconocidos ocultos), **de diagnóstico** (la del log, `diagnose` y la evidencia, sin secretos ni credenciales) y **exportable** (la de UC-22 y de las exportaciones, sin secretos salvo petición explícita del User para ese documento). Hoy la URL se guarda completa en `jobs.url` y puede llegar al log. Criterio: pruebas con URLs con usuario y contraseña, parámetros de firma y tokens que comprueban cada representación sin quitar parámetros necesarios para la descarga | Instrucción 2.6.0, §37; BR-34 |
| SUP-SEC03 | **Aceptado, sin implementar** (condicionado a D-1 y D-7): un archivo que guarde credenciales (cookies, proxy con contraseña) se crea ya restringido al usuario actual, sin un intervalo en que otros puedan leerlo. Criterio: prueba que crea el archivo y comprueba sus permisos (en Windows, su ACL) | VoiceBlueprintPro (`core/user_env.py`, creación con permisos 0600) |

## Observabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-O01 | El log se escribe en la carpeta de estado y rota (5 MB, 3 copias). **Vigente** | `command_line/log_file.py` |
| SUP-O02 | `diagnose` comprueba ffmpeg, ffprobe, yt-dlp, deno y la base de datos, y termina con código distinto de `0` si algo falla. **Vigente** | UC-01 |
| SUP-O03 | **Aceptado, sin implementar:** el diagnóstico operativo (UC-16) y la evidencia de validación (VUC-07) comparten el mismo mecanismo de recogida y de limpieza | [Análisis](requirements-analysis.md), §6 |

## Validación y reproducibilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-V01 | **Parcial** (hoy, las de los jobs y la cola; faltan las condiciones externas): toda condición de [failure-conditions.md](failure-conditions.md) que no dependa de un sitio real se prueba con pytest, fixtures y el servidor local, en cualquier sistema | [Modelo de validación](../process/validation-use-case-model.md) |
| SUP-V02 | **Aceptado, sin implementar:** quien ejecuta una prueba no emite su veredicto ([VBR-04](business-rules.md)) | VoiceStudio (arnés de sondeo) |
| SUP-V03 | **Aceptado, sin implementar:** cada mensaje real de un sitio que el producto reconoce tiene una prueba de regresión con el texto literal, incluidas sus variantes tipográficas | VoiceStudio; BR-01 |

## Interoperabilidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-I01 | **Aceptado, sin implementar:** otros programas pueden usar todas las operaciones del producto (encolar; consultar jobs, resultados y progreso; cancelar, reintentar, controlar la ejecución; perfiles, configuración, programación, diagnóstico, verificación, importación y exportación) sin interpretar texto pensado para personas. La salida JSON es un contrato de datos con su esquema, no una tabla de consola convertida. Cada comando de consulta tiene una salida JSON (`--json`), y cada comando informa los errores con un código estable, el mensaje y la acción. Los códigos de salida siguen SUP-F02. El contrato está versionado y documentado. El mecanismo adicional (API, MCP, biblioteca) es la decisión D-17. Criterio: una prueba de contrato por comando valida su JSON contra el esquema publicado | [Análisis, §12](requirements-analysis.md#12-reconciliación-de-exclusiones); YTDownload-2026 (CLI y MCP sobre una misma capa de aplicación) |
| SUP-I02 | **Aceptado, sin implementar:** el formato de intercambio de UC-22 es JSON con su versión, documentado; una versión anterior soportada se convierte al importar; nunca contiene secretos (BR-34). Criterio: pruebas de ida y vuelta por versión | UC-22 |

| SUP-I03 | **Aceptado, sin implementar:** la confianza en las entradas depende de la interfaz (§13.7 del análisis). La CLI acepta URLs locales y privadas; un documento importado se valida (SUP-SEC05); una interfaz remota futura restringe las URLs privadas por defecto. Criterio: pruebas por origen de la entrada | D-17 |
| SUP-I04 | **Aceptado, sin implementar:** las vistas, los eventos, los errores, el progreso y las capacidades que se ofrecen a los consumidores llevan la versión del contrato; los cambios compatibles solo añaden campos, y quitar o cambiar uno exige una versión mayor. No exponen el owner token, la ruta de los parciales ni secretos. Criterio: pruebas de esquema por versión y valores trampa (AAC-03, AAC-06) | D-17; [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §5 |
| SUP-I05 | **Aceptado, sin implementar:** el canal de observación entrega el job event y el estado del job después de aplicarlo; ningún consumidor recibe el transporte interno de los workers. El progreso distingue un tamaño conocido, uno estimado y uno desconocido. Criterio: pruebas del canal; regla AR-05 | [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §5.3 y §5.4 |
| SUP-I06 | **Aceptado (2.6.0), sin implementar:** el motor acepta solicitudes de otras aplicaciones con el mecanismo de cada plataforma (en Android, `SEND` y `VIEW` con `text/plain`; en iOS y Windows, el mecanismo que se cualifique) y las convierte en el mismo comando público de encolado (BR-48). Criterio: prueba del adaptador de cada plataforma con texto con una URL, con varias y sin ninguna | UC-02 A15; [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |

## Retención y privacidad

| ID | Requisito | Origen |
|---|---|---|
| SUP-D01 | **Aceptado, sin implementar:** cada clase de dato (historial, logs, caché, parciales, configuración, credenciales, respaldos, exportaciones, evidencia) tiene una retención definida y documentada (§13.14 del análisis). La del historial es configurable (UC-10 A6). Ninguna limpieza borra resultados ni reclamaciones de jobs existentes. Plazos por defecto: **pendientes de decisión** (D-21). Criterio: prueba por clase con un reloj falso | D-21 |
| SUP-D03 | **Aceptado (2.6.0), sin implementar:** cada clase de dato del producto (historial, estado operativo, datos de recuperación, metadatos de resultados, evidencia de propiedad, logs, credenciales y, cuando existan, cachés de modelos, artefactos de procesamiento y derechos de uso) tiene documentados dónde se guarda, su retención, su comportamiento en modo privado y si es exportable ([análisis, §16.4](requirements-analysis.md#164-privacidad)). El producto no recoge analítica ni telemetría. Criterio: inspección del inventario frente al esquema y las rutas de estado de cada versión | BR-49; D-21 |
| SUP-D02 | **Aceptado (2.6.0), sin implementar:** el modo privado es verificable: después de completar jobs en modo privado no queda historial terminado, búsqueda ni log de actividad de esos jobs, y un cierre a mitad de un job privado se recupera (BR-49). Criterio: prueba que recorre los almacenes de datos después de completar y de interrumpir | UC-20 A8; [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |

## Compatibilidad multimedia

| ID | Requisito | Origen |
|---|---|---|
| SUP-M01 | **Aceptado; recodificar a H.264 o HEVC condicionado a la decisión sobre patentes (R-29, D-18):** el User obtiene un resultado reproducible en sus dispositivos, por este orden de preferencia: elegir formatos compatibles del sitio (selector o preajuste), unir o cambiar el contenedor sin recodificar, convertir el audio y, solo si se pide, recodificar el video con un codificador presente en la build incluida. Criterio: con el codificador disponible, el resultado tiene el códec pedido según ffprobe; sin él, `enqueue` lo rechaza | [Análisis, §13.4](requirements-analysis.md#134-recodificación-y-compatibilidad) |

## Portabilidad y distribución

| ID | Requisito | Origen |
|---|---|---|
| SUP-C06 | La plataforma soportada es Windows 10/11 x64 (SUP-C01): la primera que se implementa y se acepta, no una restricción permanente (ADR-0032). Windows ARM64, Linux y macOS son **decisiones de soporte**. La GUI de Windows y las aplicaciones de Android e iOS son **evolución prevista**, sin implementar y con su viabilidad por cualificar ([aplicabilidad por plataforma](../design/03-target-architecture-and-evolution.md#13-aplicabilidad-por-plataforma)). Los componentes fuera de `workers`, `ffmpeg_discovery` y `command_line` no dependen de Windows. Criterio: las pruebas sin marca `windows` pasan en Linux | ADR-0004, ADR-0032 |
| SUP-C07 | La distribución es el clon con `uv sync` (ADR-0003). Publicar en PyPI es una alternativa de distribución, sin una necesidad que el procedimiento actual no cubra | Revisión de exclusiones |
| SUP-C08 | **Aceptado, sin implementar:** la parte portable de la identidad de una petición y la identidad de cada output no dependen de rutas, de su normalización ni del sistema operativo. Criterio: son iguales en dos instalaciones con rutas distintas (AAC-04, AR-06) | ADR-0033; [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §6 |
| SUP-C09 | **Aceptado, parcial:** cada responsabilidad que varía por ambiente (ejecución, terminación, almacenamiento, ubicación de la instalación, secretos, programación, avisos, multimedia) tiene su propio contrato, con un consumidor real y una suite de pruebas que cumple toda implementación; ningún contrato reúne varias. Ningún contrato funcional exige que un job sea un proceso. Criterio: AAC-05; las pruebas de `job_queue` pasan con `ScriptedWorkerPool` (hoy se cumple para `WorkerPool`, `JobStore` y `ProcessTreeTerminator`) | ADR-0032; [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §8 |
| SUP-C10 | **Aceptado, sin implementar:** una instalación existente se actualiza a cada versión nueva sin borrar su base de datos, sus reclamaciones ni su historial. Criterio: prueba de migración desde cada versión publicada del esquema (AAC-08) | [diseño, Parte 3](../design/03-target-architecture-and-evolution.md), §11.2 |
| SUP-C11 | **Aceptado (2.6.0), sin implementar:** los nombres de archivo que genera el producto son válidos en el sistema de archivos del destino (caracteres y nombres reservados, longitud y normalización de cada sistema), con un carácter de reemplazo configurable y sin una normalización única para todos los sistemas. Criterio: tabla de casos por sistema de archivos (NTFS, FAT32/exFAT, ext4, APFS y almacenamiento compartido de Android) | UC-18; GreenTuber y NewPipe (`file_rename_charset`, `file_replacement_character`), YTDLnis (`restrict_filenames`, `trim_filenames`); [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |
| SUP-C12 | **Aceptado (2.6.0), sin implementar:** cada canal de distribución tiene un perfil declarado: quién actualiza la aplicación (la aplicación o la tienda), la política de código en tiempo de ejecución (descarga iniciada por el User o solo incluido en el paquete, que afecta a UC-27), el acceso a archivos (elegidos por el User, confinado o con alcance del sandbox) y la firma. El canal se fija al construir el paquete y un canal desconocido es un error. En la distribución directa, el procedimiento documentado, con verificación de firma o hash si se publican paquetes. Criterio: tabla de canales con su perfil y prueba de la comprobación con un canal simulado | UC-32; NewPipe (`NewVersionWorker`), Open Video Downloader (`updater_*`), VoiceStudio (`config/distributions.mjs`); [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |
| SUP-C13 | **Aceptado (2.6.0), sin implementar:** el paquete Android cumple las condiciones técnicas vigentes de Google Play si ese canal se elige: target API exigido (Android 16, API 36, para apps nuevas y actualizaciones desde el 31 de agosto de 2026) y bibliotecas nativas compatibles con páginas de 16 KB (apps con target API 35 o más). Criterio: comprobación del paquete con el analizador de APK y la alineación de cada `.so` | R-36; fuentes oficiales en el [análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250) |

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
