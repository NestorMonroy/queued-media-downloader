# Catálogo de condiciones de fallo

- **Fase RUP:** Elaboración (consolidación de requisitos)
- **Versión:** 1.3 (2026-11-26; `Retry-After`, autenticación y directos según las resoluciones aprobadas). 1.2: separa las condiciones de almacenamiento y documenta la cadena de causas
- **Responsabilidad:** autoridad única sobre qué condiciones impiden o interrumpen una descarga, a qué alcanzan y qué garantiza el producto ante cada una. Los casos de uso enlazan aquí en lugar de repetirlo: UC-03 A2, UC-06, UC-11, UC-15 E2 y UC-17.
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
| **Garantía** | Lo que el producto debe asegurar; es el criterio de aceptación. *(P)* indica que pertenece al alcance aceptado y no está implementada |

El motivo del job lo asigna `failure_classifier` con la causa más interna de la excepción de yt-dlp. Se comprobó con excepciones reales de yt-dlp 2026.11.23:
- un `HTTPError` 403, 429 o 503 es `NETWORK`, y uno 404 o 410 es `UNAVAILABLE`;
- un error de TLS o de proxy es `NETWORK`;
- un `ExtractorError` esperado es `UNAVAILABLE`, aunque sea la comprobación antibots;
- un `OSError` que llega por `exc_info` es `FILESYSTEM`, sin distinguir la condición; si yt-dlp lo pierde o lo deja en `__context__`, es `UNKNOWN` (§3.2);
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
| Transmisión en directo o programada | `is_live`, `live_status`, `release_timestamp` | Job · un worker ocupado sin final previsible | **Sin regla**: el worker descarga mientras dure (R-26) | D-10, BR-24: la programada se aplaza sin ocupar un worker; la activa, con una duración máxima; la interrumpida continúa desde el momento actual |
| Resolución de los retos JavaScript de YouTube | Falta deno, o yt-dlp-ejs falla | Sitio · persistente | yt-dlp avisa de que pueden faltar formatos; `diagnose` falla con `CHALLENGE_SOLVER_NOT_FOUND` (T42-D3) | Igual; la actualización de yt-dlp-ejs sigue SUP-S01 |

**Propuesta (instrucción 2.5.0, pendiente de aprobación):** NewPipeExtractor distingue además contenido de pago, contenido de miembros de un servicio premium, cuenta cerrada y confirmación de no ser un bot (`PaidContentException`, `YoutubeMusicPremiumContentException`, `AccountTerminatedException`, `SignInConfirmNotBotException`). La versión Electron de Open Video Downloader (`errorDefinitions.json`, 47 definiciones) añade contenido con DRM y contenido solo incrustable, que el catálogo tampoco distingue. Separarlos en el catálogo permitiría decir al User si un perfil de acceso (UC-19) puede ayudar; requiere cualificar los mensajes de yt-dlp que corresponden a cada uno ([análisis, §15](requirements-analysis.md#15-descubrimiento-funcional-250)).

## 2. Red y acceso al sitio

| Condición | Causa y detección | Alcance · temporalidad | Hoy | Garantía e información al User |
|---|---|---|---|---|
| Restricción del sitio: antibots, captcha o límite de peticiones | Texto de yt-dlp ([BR-01](business-rules.md)) | Sitio · transitoria (hasta una hora, según yt-dlp) | `FAILED` `UNAVAILABLE`; los jobs siguientes del sitio también fallan (T42, paso 5.7) | *(P)* UC-11 A1: aplazar sin gastar intentos, no insistir y continuidad selectiva |
| HTTP 429, o 503 con `Retry-After` | `HTTPError` en la cadena; cabecera `Retry-After` en `HTTPError.response` (yt-dlp no la usa) | Sitio · transitoria, con el plazo informado | `FAILED` `NETWORK` | *(P)* BR-41: sin peticiones al sitio antes del plazo; después, BR-03 |
| Inicio de sesión requerido o sesión caducada | Texto de yt-dlp («Sign in», «login required») sin las firmas de BR-01; con un perfil de acceso, después de usarlo | Job o sitio · persistente hasta renovar las credenciales | `FAILED` `UNAVAILABLE` | *(P)* UC-19 A6: se informa la renovación necesaria; no se repiten peticiones ni se prueban otras credenciales (BR-41) |
| HTTP 403 del servidor de video | `HTTPError` 403 tras una extracción correcta | Job o sitio · incierta: firma caducada, cliente sin PO Token (R-20) | `FAILED` `NETWORK` | *(P)* Un motivo que no sugiera reintentar sin más; un 403 no se trata como restricción temporal salvo que BR-01 la reconozca (BR-41, D-4). Sin cambiar de cliente: la alternativa de VoiceStudio exige PO Token en `android` |
| HTTP 5xx | `HTTPError` 5xx | Sitio · transitoria | **Divergencia**: 0 reintentos, `FAILED` `NETWORK` | Los reintentos de yt-dlp, con la paridad de BR-07 *(P, SUP-R11)* |
| Timeout o conexión cortada con un host | `TransportError`, `TimeoutError` | Job · transitoria | **Divergencia**: 0 reintentos (T42-D7: un timeout falló a la primera) | Igual que la fila anterior |
| Agotamiento de los reintentos del downloader | `DownloadError` con "[download] Got error" | Job · transitoria | `FAILED` `NETWORK` (T42-D7 corregido) | Igual |
| Corte de conectividad (DNS, red inalcanzable, conexión rechazada) | `getaddrinfo` (11001 en Windows), `ECONNREFUSED`, `ENETUNREACH` ([BR-05](business-rules.md)) | Cola · transitoria | `FAILED` `NETWORK`; los jobs siguientes también (T42, paso 5.2: 8 jobs) | *(P)* UC-11 A2 |
| TLS interceptado (proxy de empresa o antivirus) | `SSLError` | Cola · persistente | `FAILED` `NETWORK` | *(P)* Un mensaje que distinga la causa, como hace VoiceStudio; `diagnose` informa del proxy (D-7) |
| Proxy mal configurado o SOCKS sin soporte | `ProxyError` | Cola · persistente | `FAILED` `NETWORK` | *(P)* Igual que la fila anterior |

## 3. Almacenamiento y archivos

Las condiciones de almacenamiento no son una sola. Difieren en naturaleza, alcance y forma de recuperarse, y por eso se tratan por separado ([UC-17](use-cases/uc-17-preserve-work-under-storage-failures.md)). Una comprobación previa sirve para prevenir, pero no garantiza que la condición se mantenga durante la descarga: otro programa puede llenar la unidad, retirarse una unidad extraíble o cambiar un permiso a mitad del job. Cada condición tiene, por tanto, un tratamiento preventivo (antes de enviar el job) y otro reactivo (cuando falla una escritura).

### 3.1 Condiciones

En Windows, Python traduce varios códigos `winerror` al mismo `errno`: los errores 5, 32 y 33 llegan como `EACCES`, y el 112 y el 39, como `ENOSPC`. Para distinguirlos hay que leer `winerror`, no solo `errno`. Las traducciones marcadas *por confirmar* se verifican con una prueba `windows` en la campaña.

| Condición | Naturaleza | Detección | Alcance · temporalidad | Prevención | Hoy | Tratamiento propuesto e información al User |
|---|---|---|---|---|---|---|
| `ENOSPC` | Espacio insuficiente en la unidad | `errno` 28 en la cadena de causas, o «No space left on device» en el texto de ffmpeg | Unidad · persiste hasta que se libera espacio; puede aparecer a mitad del job aunque la comprobación previa pasara | Espacio libre frente al tamaño estimado del job (BR-28) | `FAILED` `FILESYSTEM`, o `UNKNOWN` si yt-dlp perdió la causa (§3.2); los jobs siguientes de la unidad fallan igual | *(P)* Aplazar el job sin gastar intentos y dejar de enviar los jobs de esa unidad (BR-09). El mensaje nombra la unidad, el espacio libre y el que necesitaba el job, si se conoce |
| `EDQUOT` | Cuota de almacenamiento del usuario excedida (la unidad puede tener espacio libre) | `errno` 122 en Linux; en Windows, `winerror` 1295 (`ERROR_DISK_QUOTA_EXCEEDED`), *por confirmar*; o «Disk quota exceeded» en el texto | Unidad para ese usuario · persiste hasta liberar espacio propio o ampliar la cuota | Parcial: el espacio libre de la unidad no refleja la cuota | Como `ENOSPC` | *(P)* Como `ENOSPC`, pero el mensaje dice que es la cuota del usuario, no la unidad: liberar espacio en otra carpeta de la unidad no siempre ayuda |
| `winerror` 112 (`ERROR_DISK_FULL`) | Disco lleno | `winerror` 112 (Python lo traduce a `ENOSPC`) | Como `ENOSPC` | Como `ENOSPC` | Como `ENOSPC` | Como `ENOSPC` |
| `winerror` 39 (`ERROR_HANDLE_DISK_FULL`) | Disco lleno, informado al escribir por un handle abierto | `winerror` 39 (traducción a `ENOSPC` *por confirmar*) | Como `ENOSPC` | Como `ENOSPC` | Como `ENOSPC` | Como `ENOSPC` |
| `winerror` 5 (`ERROR_ACCESS_DENIED`) | Acceso denegado. **Requiere el contexto**: permisos de la carpeta, archivo de solo lectura, acceso controlado a carpetas de Microsoft Defender, archivo marcado para eliminación, o carpeta en lugar de archivo | `winerror` 5 (llega como `EACCES`, igual que 32 y 33) | Carpeta o archivo · persistente salvo que el contexto cambie | Sí para la carpeta (escribir y borrar un archivo de prueba); no para un archivo concreto | yt-dlp lo reintenta como `EACCES` (`file_access_retries`); después, `FAILED` `FILESYSTEM` o `UNKNOWN` | *(P)* No aplazar: reintentar sin cambiar nada no sirve. El mensaje nombra la ruta y las causas posibles según la operación (crear la carpeta, abrir el parcial, mover el archivo final). Decisión D-12 |
| `winerror` 32 (`ERROR_SHARING_VIOLATION`) | Conflicto de uso compartido: otro proceso tiene abierto el archivo (antivirus, indexador, reproductor, cliente de sincronización) | `winerror` 32 (llega como `EACCES`) | Archivo · normalmente transitorio; persistente si un programa lo mantiene abierto | No | `file_access_retries` = 10 de yt-dlp; al agotarlos, `UNKNOWN` (§3.2) | Reintentos de yt-dlp (BR-26). Si persisten, `FAILED` con un mensaje que nombra el archivo y sugiere cerrarlo o excluir la carpeta de la sincronización o del antivirus |
| `winerror` 33 (`ERROR_LOCK_VIOLATION`) | Conflicto de bloqueo: otro proceso bloqueó una región del archivo | `winerror` 33 (llega como `EACCES`) | Como `winerror` 32 | No | Como `winerror` 32 | Como `winerror` 32 |
| Directorio inexistente | Configuración (la carpeta configurada no existe y no se puede crear) o disponibilidad (la unidad o el recurso de red no está). yt-dlp crea las carpetas que faltan; falla si no puede | `ENOENT`, `winerror` 3 (`ERROR_PATH_NOT_FOUND`); `winerror` 21 (`ERROR_NOT_READY`) o 53 (`ERROR_BAD_NETPATH`) para una unidad ausente, *por confirmar* | Unidad · persistente; recuperable si la unidad vuelve | Sí: existe o se puede crear (UC-01 A10, BR-28) | `FAILED` `FILESYSTEM` («Unable to create directory») | *(P)* Configuración: no aplazar; el mensaje nombra la clave (`download_directory`, `state_directory`). Unidad ausente: como una condición de la unidad, aplazar sus jobs (D-12) |
| Directorio no escribible | Permisos o restricciones: ACL, unidad de solo lectura (`EROFS`, `winerror` 19), acceso controlado a carpetas | `EACCES`, `EROFS`, `winerror` 5 o 19 | Carpeta o unidad · persistente | Sí: escribir y borrar un archivo de prueba (BR-28) | `FAILED` `FILESYSTEM`, o `UNKNOWN` | *(P)* No aplazar; el mensaje nombra la carpeta y la restricción |
| Permiso de almacenamiento revocado (plataformas futuras) | El sistema retira el acceso a un recurso que el User eligió antes: un URI de SAF en Android, un bookmark en iOS ([diseño, Parte 3, §8.8](../design/03-target-architecture-and-evolution.md#88-almacenamiento-d-5-d-11-d-12)) | Excepción de acceso al resolver la referencia de almacenamiento (por cualificar en cada plataforma) | Destino · persistente hasta que el User conceda de nuevo el acceso | Comprobar el acceso al admitir el job | No aplica en Windows | *(P)* Como «directorio no escribible»: no se envían jobs a ese destino, se indica cómo volver a conceder el acceso y los outputs no verificables no cuentan como completos (D-9). No es una excepción de plataforma ni un estado nuevo |
| Punto de montaje no confiable en la ruta (Dev Drive, VHD montado, unión a otro perfil) | Regla de Windows sobre el volumen | `winerror` 448 | Unidad · persistente | Sí, en `diagnose` (UC-01 A10) | **Sin cualificar**: `FAILED` `FILESYSTEM` | *(P)* No aplazar; el mensaje dice que es una regla de Windows sobre el volumen. Origen: VoiceStudio y VoiceBlueprintPro (`WINDOWS_UNTRUSTED_MOUNT`) |
| La unidad del estado se llena | La base de datos o el log no pueden escribirse | `sqlite3.OperationalError` («database or disk is full», `SQLITE_FULL`) u `OSError` del log | Cola · persiste hasta liberar espacio | Sí: espacio en la unidad del estado (BR-28) | `run` termina con un error | *(P)* UC-17 E1: `run` termina con código `1` y nombra la unidad; los jobs quedan `RUNNING` y se recuperan (UC-06) |
| Nombre final de otro job o archivo que el job no escribió | Propiedad (ADR-0030) | Reclamación ajena o archivo existente | Job · persistente | Sí: la reclamación se hace antes de descargar | `FAILED` `FILESYSTEM` sin tocar el archivo (UC-03 A7) | Igual |
| Descarga sin un archivo final utilizable | Resultado inválido | Sin ruta, vacío o dentro de la carpeta de parciales | Job · definitiva | No | `FAILED` `FILESYSTEM`, parciales conservados (UC-03 A8) | Igual |
| Ruta demasiado larga | Límite de Windows (260 caracteres sin rutas largas activadas) | `winerror` 206 o 3 | Job · persistente | Sí: recorte del nombre | Recorte con `trim_file_name` (`max_filename_length` = 150) | Igual; pruebas `windows` (campaña, paso 11) |

### 3.2 Cómo llega la información: la cadena de causas

yt-dlp envuelve los errores y, en algunos caminos, pierde el original. Se comprobó con yt-dlp 2026.11.23 (2026-11-26), provocando cada error en el mismo punto del código de yt-dlp y pasándolo por el clasificador actual:

| Camino | Lugar en yt-dlp | Dónde queda el `OSError` | Motivo que asigna hoy el clasificador |
|---|---|---|---|
| Escritura de datos de la descarga | `downloader/http.py`, «unable to write data» | `DownloadError.exc_info` | `FILESYSTEM` (sin distinguir la condición) |
| Crear la carpeta de destino | `YoutubeDL._ensure_dir_exists`, «Unable to create directory» | `DownloadError.exc_info` | `FILESYSTEM` |
| Abrir o renombrar un archivo tras agotar `file_access_retries` | `downloader/common.py`, `wrap_file_access` | **En ningún sitio**: el error se informa fuera del bloque `except`, y solo queda el texto | **`UNKNOWN`** |
| Otro `OSError` al procesar el contenido | `YoutubeDL.process_info`, `raise UnavailableVideoError(err)` | En `__context__` del `UnavailableVideoError` que guarda `exc_info` | **`UNKNOWN`** |
| ffmpeg al unir o extraer audio | `postprocessor/ffmpeg.py`, `FFmpegPostProcessorError` | No hay `OSError`: solo la última línea del error de ffmpeg | `POSTPROCESSING` |

Consecuencias:
- El clasificador actual solo recorre `DownloadError.exc_info`. Una condición de almacenamiento puede terminar como `UNKNOWN` o `POSTPROCESSING`, y el User no sabe que el problema es la unidad. Es una **divergencia** (R-28).
- La identificación debe recorrer toda la cadena: `exc_info`, `__cause__` y `__context__`, y como último recurso el texto del mensaje ([BR-25](business-rules.md)). Es el mismo principio que usa VoiceStudio para el disco lleno, y la misma lección que dejó T42-D7 con los reintentos de red agotados.
- Como los textos dependen de yt-dlp y de ffmpeg, cada uno tiene una prueba de contrato con el texto real (SUP-V03), que detecta su cambio al actualizar yt-dlp (SUP-S01).

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
