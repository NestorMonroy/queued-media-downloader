# Catálogo de condiciones de fallo

- **Fase RUP:** Elaboración (consolidación de requisitos)
- **Versión:** 1.1 (2026-11-26; añade las condiciones encontradas en YTDownload-2026 y VoiceBlueprintPro)
- **Responsabilidad:** autoridad única sobre qué condiciones impiden o interrumpen una descarga, a qué alcanzan y qué garantiza el producto ante cada una. Los casos de uso enlazan aquí en lugar de repetirlo: UC-03 A2, UC-06, UC-11 y UC-15 E2.
- **Técnicas (BABOK v3):** 10.40 Root Cause Analysis, 10.44 State Modelling, 10.16 Decision Modelling, 10.1 Acceptance and Evaluation Criteria
- **Mecanismos actuales:**
  - `jobs.FailureReason`;
  - `media_extraction.failure_classifier`;
  - los job events `JobFailed`, `JobCompleted` y `JobCancelled`;
  - el ciclo de vida del [vocabulario, §1.1](../design/00-vocabulary.md#11-estados-terminados-reintentables-y-cancelables).

## Cómo leer el catálogo

| Columna | Significado |
|---|---|
| **Alcance** | Job: solo ese job. Sitio: los jobs del mismo sitio. Unidad: los que escriben en esa unidad. Cola: todos. Instalación: nada puede ejecutarse |
| **Temporalidad** | Transitoria: desaparece sola. Persistente: necesita una acción. Definitiva: no se arregla reintentando |
| **Hoy** | Comportamiento comprobado en el código vigente (`main`) y su `FailureReason`. "Sin cualificar" indica que nadie ha decidido el comportamiento |
| **Garantía** | Lo que el producto debe asegurar; es el criterio de aceptación. *(P)* indica que es propuesta y no está implementada |

El motivo del job lo asigna `failure_classifier` con la causa más interna de la excepción de yt-dlp. Se comprobó con excepciones reales de yt-dlp 2026.11.23:
- un `HTTPError` 403, 429 o 503 es `NETWORK`, y uno 404 o 410 es `UNAVAILABLE`;
- un error de TLS o de proxy es `NETWORK`;
- un `ExtractorError` esperado es `UNAVAILABLE`, aunque sea la comprobación antibots;
- `OSError` 28 es `FILESYSTEM`;
- un `DownloadError` sin causa es `UNKNOWN`, salvo el agotamiento de reintentos del downloader (T42-D7).

## 1. Extracción y contenido

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| Extractor desactualizado | `ExtractorError` inesperado | Sitio · persistente hasta actualizar yt-dlp | `FAILED` `EXTRACTOR_OUTDATED`, mensaje que sugiere actualizar (UC-03 A3) | Igual; además, una indicación de que reintentar no sirve hasta actualizar *(P, SUP-U05)*. La actualización la hace el Mantenedor (SUP-S01) o el User (decisión D-8) |
| URL no soportada | `UnsupportedError` | Job · definitiva | `FAILED` `UNSUPPORTED_URL` | Igual; reintentar no sirve |
| Contenido eliminado o no disponible | `ExtractorError` esperado; HTTP 404 o 410 | Job · definitiva | `FAILED` `UNAVAILABLE` | Igual. En una playlist, si el sitio la marca no disponible en la lista, la entrada se crea `SKIPPED` (UC-04 A3) |
| Contenido privado, con restricción de edad o solo para miembros | `ExtractorError` esperado ("This video is only available for registered users", entre otros) | Job · persistente (necesita una cuenta) | `FAILED` `UNAVAILABLE` | Igual; no es una restricción del sitio (BR-01). Sin cuentas mientras D-1 siga abierta |
| Restricción geográfica | `GeoRestrictedError` | Job · persistente | `FAILED` `GEO_RESTRICTED` | Igual. Sin evasión: el proxy solo se acepta como conectividad legítima (D-7) |
| Formato guardado ya no disponible al reanudar | `ExtractorError` con "Requested format is not available" | Job · recuperable | Un reintento con el selector original (UC-06 A1) | Igual |
| Transmisión en directo o programada | `is_live`, `live_status` | Job · un worker ocupado sin final previsible | **Sin cualificar**: no hay una regla para los directos (riesgo R-26) | Decisión D-10: rechazarla con un mensaje, grabar hasta que termine con un límite, o esperar al inicio (`wait_for_video`) |
| Resolución de los retos JavaScript de YouTube | Falta deno, o yt-dlp-ejs falla | Sitio · persistente | yt-dlp avisa de que pueden faltar formatos; `diagnose` falla con `CHALLENGE_SOLVER_NOT_FOUND` (T42-D3) | Igual; la actualización de yt-dlp-ejs sigue SUP-S01 |

## 2. Red y acceso al sitio

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| Restricción del sitio: antibots, captcha o límite de peticiones | Texto de yt-dlp ([BR-01](business-rules.md)) | Sitio · transitoria (hasta una hora, según yt-dlp) | `FAILED` `UNAVAILABLE`; los jobs siguientes del sitio también fallan (T42, paso 5.7) | *(P)* UC-11 A1: aplazar sin gastar intentos, no insistir y continuidad selectiva |
| HTTP 429 | `HTTPError` 429 | Sitio · transitoria | `FAILED` `NETWORK` | *(P)* Tratarlo como restricción del sitio (BR-01) |
| HTTP 403 del servidor de video | `HTTPError` 403 tras una extracción correcta | Job o sitio · incierta: firma caducada, cliente sin PO Token (R-20) | `FAILED` `NETWORK` | *(P)* Un motivo que no sugiera reintentar sin más. Sin cambiar de cliente: la alternativa de VoiceStudio exige PO Token en `android` |
| HTTP 5xx | `HTTPError` 5xx | Sitio · transitoria | **Divergencia**: 0 reintentos, `FAILED` `NETWORK` | Los reintentos de yt-dlp, con la paridad de BR-07 *(P, SUP-R11)* |
| Timeout o conexión cortada con un host | `TransportError`, `TimeoutError` | Job · transitoria | **Divergencia**: 0 reintentos (T42-D7: un timeout falló a la primera) | Igual que la fila anterior |
| Agotamiento de los reintentos del downloader | `DownloadError` con "[download] Got error" | Job · transitoria | `FAILED` `NETWORK` (T42-D7 corregido) | Igual |
| Corte de conectividad (DNS, red inalcanzable, conexión rechazada) | `getaddrinfo` (11001 en Windows), `ECONNREFUSED`, `ENETUNREACH` ([BR-05](business-rules.md)) | Cola · transitoria | `FAILED` `NETWORK`; los jobs siguientes también (T42, paso 5.2: 8 jobs) | *(P)* UC-11 A2 |
| TLS interceptado (proxy de empresa o antivirus) | `SSLError` | Cola · persistente | `FAILED` `NETWORK` | *(P)* Un mensaje que distinga la causa, como hace VoiceStudio; `diagnose` informa del proxy (D-7) |
| Proxy mal configurado o SOCKS sin soporte | `ProxyError` | Cola · persistente | `FAILED` `NETWORK` | *(P)* Igual que la fila anterior |

## 3. Almacenamiento y archivos

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| Disco lleno o cuota agotada | `ENOSPC`, `EDQUOT`, `winerror` 112 o 39, o el mensaje de ffmpeg ([BR-08](business-rules.md)) | Unidad · persistente hasta liberar espacio | `FAILED` `FILESYSTEM` y los jobs siguientes también | *(P)* UC-11 A3; el mensaje nombra la unidad y el espacio libre |
| Permiso denegado, carpeta inexistente, unidad desconectada | `EACCES`, `ENOENT`, `winerror` 5 o 3 | Unidad o cola · persistente | `FAILED` `FILESYSTEM` | *(P)* Comprobar el destino antes de enviar el job (VoiceStudio, #1225); el mensaje nombra la carpeta y dice que reintentar no sirve |
| Archivo bloqueado un instante (antivirus, indexador) | `winerror` 32 o 33 | Job · transitoria | `file_access_retries` = 10 de yt-dlp | Igual |
| Archivo bloqueado por más tiempo (cliente de sincronización como OneDrive, antivirus con análisis largo) | `winerror` 32 o 33 tras agotar `file_access_retries` | Unidad · persistente mientras dure el bloqueo | `FAILED` `FILESYSTEM` | *(P)* El mensaje nombra la carpeta y sugiere excluirla de la sincronización o del antivirus; reintentar sin cambiar nada no sirve (SUP-U05). Origen: VoiceStudio y VoiceBlueprintPro (`VIDEO_DOWNLOAD_OS_ERROR`) |
| Punto de montaje no confiable en la ruta (Dev Drive, VHD montado, unión a otro perfil) | `winerror` 448 | Unidad · persistente | **Sin cualificar**: `FAILED` `FILESYSTEM` | *(P)* El mensaje nombra la carpeta y dice que es una regla de Windows sobre el volumen; `diagnose` lo detecta en las carpetas configuradas (UC-01 A10). Origen: VoiceStudio y VoiceBlueprintPro (`WINDOWS_UNTRUSTED_MOUNT`) |
| Nombre final de otro job o archivo que el job no escribió | Reclamación ajena o archivo existente (ADR-0030) | Job · persistente | `FAILED` `FILESYSTEM` sin tocar el archivo (UC-03 A7) | Igual |
| Descarga sin un archivo final utilizable | Sin ruta, vacío o dentro de la carpeta de parciales | Job · definitiva | `FAILED` `FILESYSTEM`, parciales conservados (UC-03 A8) | Igual |
| Ruta demasiado larga | Más de 260 caracteres en Windows | Job · persistente | Recorte con `trim_file_name` (`max_filename_length` = 150) | Igual; pruebas `windows` (campaña, paso 11) |

## 4. Procesos y herramientas

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| ffmpeg ausente o roto | Verificación al arrancar (ADR-0006) | Instalación · persistente | `run` termina con código `2` sin ejecutar jobs | Igual |
| ffmpeg falla en la unión o al extraer el audio | `PostProcessingError` | Job · según la causa | `FAILED` `POSTPROCESSING`, parciales conservados | Igual. Si la causa es el disco lleno, es la fila del disco lleno *(P)* |
| Un worker muere | El pool detecta la caída | Job · transitoria | `FAILED` `WORKER_CRASHED` y un worker de reemplazo (UC-03 A4) | Igual |
| Un worker no se registra en su Job Object | Fallo de `AssignProcessToJobObject` | Cola · transitoria | 3 intentos; si todos fallan, código `1` y los jobs se recuperan (R-19) | Igual |
| Otro programa retiene la base de datos | `database is locked` más allá de `busy_timeout` | Cola · transitoria | `run` espera y avisa (UC-03 A10, T42-D12); los comandos cortos terminan con código `1` sin cambios | Igual |
| La base de datos no se abre o falla una migración | `sqlite3.DatabaseError` | Instalación · persistente | Migración deshecha, código `1` (UC-01 A8) | Igual |

## 5. Interrupciones e integridad local

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| `Ctrl+C`, cierre de la terminal o corte de luz | Interrupción del proceso principal | Cola · recuperable | Los jobs quedan `RUNNING`; el siguiente `run` los recupera y reanuda (UC-06) | Igual |
| El equipo se suspende con jobs en curso | Suspensión de Windows | Cola · recuperable | **Sin cualificar**: sin prevención; al despertar, errores de red que gastan los jobs | *(P)* Impedir la suspensión mientras hay jobs en curso (SUP-R08); al despertar, UC-11 A2 |
| La descarga y la unión terminan, pero no se registra `JobCompleted` | Cierre o fallo de la base de datos entre mover el archivo y guardar el estado (T42-D12) | Job · recuperable | El siguiente `run` lo envía de nuevo: yt-dlp **vuelve a extraer del sitio**, ve el archivo y el job termina `COMPLETED` (UC-06 A4). Si el sitio no responde, el job falla aunque el archivo esté completo (T42, cola 5.7-r2) | *(P)* UC-06 A11: completar sin consultar el sitio cuando la evidencia local basta (decisión D-9) |
| Base de datos restaurada de una copia | Ids reutilizados | Cola | Owner token; nada se hereda (UC-06 A8) | Igual |
| Archivo final reclamado por varios jobs (base de E1) | Migración 0004 | Job | Todos `FAILED`, sin dueño (UC-06 A7) | Igual |
| El archivo final de un job `COMPLETED` ya no existe | El User lo movió | Job | Nada cambia (UC-06 A9) | Igual |

## 6. Información al User en cada fallo

Hoy cada fallo se muestra con su motivo y su mensaje (UC-08, UC-09, SUP-U01). Falta indicar si reintentar sirve y qué acción lo resuelve (SUP-U05, propuesto). En VoiceStudio, cada clase de fallo trae esa indicación.
