# Referencia: casos de uso y flujos de VoiceStudio

- **Proyecto analizado:** [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio), commit `d9061408c20406dfb1b1cbb80450549533c70b0a` (2026-11-26), clonado en el espacio de análisis (`/tmp/VoiceStudio`)
- **Licencia:** AGPL-3.0. **Solo se toman ideas**; no se copia código a este proyecto (The Unlicense, ADR-0007)
- **Técnicas (BABOK v3):** 10.4 Benchmarking and Market Analysis, 10.18 Document Analysis, 10.22 Functional Decomposition, 10.47 Use Cases and Scenarios
- **Fecha:** 2026-11-26
- **Relacionado:** [análisis del funcionamiento sin vigilancia](../unattended-operation-analysis.md), [modelo de casos de uso](../use-case-model.md), [reglas de negocio](../business-rules.md)

Los casos de uso se reconstruyen desde el código, las pruebas y la documentación de VoiceStudio. No hay especificación de casos de uso en el proyecto original. Cada flujo cita su evidencia. El número de un fallo reportado (`#2034`) es el de su repositorio.

---

## 1. Qué es VoiceStudio

Aplicación de voz con IA: clonar, diseñar voces, doblar, dictar, transcribir y narrar. Es una app de escritorio (Electron) y móvil, con un backend en Python (FastAPI) que corre en el mismo equipo. Usa yt-dlp en dos sitios:
- **Doblaje** (importar un video desde una URL): yt-dlp como **biblioteca**, en `backend/services/dub_pipeline.py`, función `yt_download_sync`.
- **Galería de voces** (buscar y recortar clips): yt-dlp por **línea de comandos** en un subproceso, en `backend/api/routers/gallery.py`.

Es un programa interactivo: el usuario importa un video cada vez. No es un descargador de colas ni de playlists.

## 2. Inventario completo (10.22)

Funcionalidades del catálogo del propio proyecto (`docs/features.yaml`, `docs/feature-catalog.md`) y capacidades de soporte encontradas en `backend/api/routers/`. **Dominio** indica si comparte el dominio de queued-media-downloader (obtener contenidos de sitios y operar esa obtención).

| Funcionalidad | Routers o módulos | Dominio | Motivo |
|---|---|---|---|
| Video Dubbing | `dub_core`, `dub_translate`, `dub_generate`, `dub_export` | **Parcial:** solo la importación (VS-UC-01, VS-UC-02) | Transcribir, traducir, generar y exportar son procesamiento de IA |
| Batch Queue | `batch` | **Parcial:** la operación de la cola (VS-UC-05 a VS-UC-09) | Lo que procesa (doblaje) queda fuera; la cola se compara con la nuestra |
| Galería de voces (búsqueda y descarga de clips) | `gallery` | **Sí** (VS-UC-03, VS-UC-04) | Busca y descarga de YouTube con yt-dlp |
| Herramientas de medios (ffmpeg, ffprobe, yt-dlp) | `media_tools`, `services/media_tools.py` | **Sí** (VS-UC-11, VS-UC-12) | Equivalente a nuestro UC-01 y a la actualización de yt-dlp (SUP-S01) |
| Autodiagnóstico y paquete de diagnóstico | `system`, `core/diagnose.py`, `core/diagnostic_bundle.py` | **Sí** (VS-UC-14, VS-UC-15) | Equivalente a `diagnose` (UC-01) |
| Entorno del usuario (proxy, tokens) | `core/user_env.py`, `settings` | **Sí** (VS-UC-13) | Proxy y variables para yt-dlp |
| Recuperación tras un reinicio | `core/job_store.py` | **Sí** (VS-UC-10) | Equivalente a UC-06 |
| Remote Model Downloads | `services/model_manager.py`, `sidecar_install.py` | Patrones solamente | Descargas de modelos (Hugging Face): reintentos, réplicas, descargas interrumpidas |
| Voice Cloning, Voice Design | `generation`, `profiles`, `personas`, `describe_voice` | No | Síntesis de voz |
| Dictation Widget | `dictation`, `capture`, `capture_ws` | No | Reconocimiento de voz en tiempo real |
| Vocal Isolation, Speaker Diarization | Etapas del doblaje (Demucs, diarización) | No | Procesamiento de audio |
| MCP Server, OpenAI/ElevenLabs compatibles | `mcp_bindings`, `openai_compat`, `elevenlabs_compat` | No | Interfaces de programación |
| AI Watermark | `watermark` | No | Marca de agua del audio generado |
| Local-first, GPU Auto-Detect, Extensible | `engines`, `core/gpu_*` | No | Ejecución de modelos |
| Audiolibros, historias, proyectos, llamadas, telefonía, marketplace, comunidad, sincronización en la nube, traducción | `audiobook`, `stories`, `projects`, `calls`, `telephony_twilio`, `marketplace`, `community`, `cloud_sync`, `sonitranslate`, etc. | No | Producto de voz |

## 3. Actores

| Actor | Tipo | Descripción |
|---|---|---|
| **Usuario** | Principal | Persona que usa la app de escritorio |
| **Sitio de medios** | Secundario | YouTube y otros sitios soportados por yt-dlp |
| **PyPI** | Secundario | De donde la app descarga la última versión de yt-dlp (VS-UC-12) |
| **Repositorio de ffmpeg** | Secundario | `zackees/ffmpeg_bins`, commit fijado y SHA-256 verificado (VS-UC-11) |
| **Mantenedor** | Secundario | Recibe el paquete de diagnóstico en un reporte (VS-UC-15) |

## 4. Casos de uso en el dominio

### VS-UC-01 Importar un video desde una URL

- **Objetivo:** el video de una URL queda descargado, reproducible en la app y con su audio preparado para el doblaje.
- **Actor principal:** Usuario. **Secundario:** Sitio de medios.
- **Disparador:** el Usuario pega una URL en la pestaña Dub (`docs/electron-dubbing.md`).
- **Precondiciones:** yt-dlp importable; la carpeta de datos se puede escribir.
- **Flujo básico** (`dub_core.dub_ingest_url`, `dub_pipeline.ingest_pipeline` y `yt_download_sync`):
  1. El Usuario envía la URL, y opcionalmente un `cookies.txt`, pedir subtítulos y el idioma de origen.
  2. El sistema valida la URL: esquema `http(s)` y que todas las respuestas DNS sean públicas (`url_safety.check_public_url`).
  3. Comprueba que yt-dlp esté instalado.
  4. Crea la carpeta del trabajo.
  5. Encola una tarea en segundo plano y responde al momento (`202`) con el id del trabajo y de la tarea.
  6. La tarea vuelve a validar la URL y comprueba de antemano que la carpeta de destino exista y se pueda escribir (#1225).
  7. Descarga con yt-dlp como biblioteca. Publica el progreso por un canal de eventos (`/tasks/stream/{task_id}`) y deja todos los mensajes de yt-dlp en el log, sin depender de stdout ni stderr.
  8. Si los códecs no se reproducen en el navegador integrado, transcodifica el video.
  9. Si se pidieron subtítulos, los descarga en una segunda pasada que puede fallar sin detener la importación.
  10. Borra la exportación de cookies, antes de las etapas largas de audio.
  11. Extrae el audio.
  12. Calcula el hash del contenido y, si coincide con un trabajo anterior, reutiliza sus resultados (separación, miniatura, escenas).
  13. Separa la voz del fondo y detecta las escenas.
  14. Publica `ready`.
- **Flujos alternativos:**
  - **A1. Con cookies** (paso 1): el `cookies.txt` se valida (formato Netscape, máximo 1 MB) y se guarda en un archivo temporal privado (permisos 0600). Solo se acepta por HTTPS o desde la interfaz local. Se borra al terminar, al fallar o al cancelar (`_stage_cookie_export`, `_delete_cookie_export`; 11 pruebas en `tests/test_youtube_cookie_import.py`).
  - **A2. Fallo de red** (paso 7): "broken pipe", "connection reset", "timed out", "unable to download video", "remote end closed" o "the page needs to be reloaded". Borra los parciales y reintenta hasta 2 veces, tras 2 s y 4 s (`_YT_DOWNLOAD_RETRIES = 2`; `tests/test_dub_download_retry.py`).
  - **A3. 403 o "DRM protected"** (paso 7; #625, #1254): cambia de cliente de YouTube (`tv`, luego `android`, luego `web_safari`) sin gastar los reintentos de red (`tests/test_dub_download_403.py`, `tests/test_yt_drm_escalation.py`).
  - **A4. Contenido ya importado** (paso 12): reutiliza los resultados del trabajo anterior y publica `cached`.
  - **A5. Archivo local en lugar de URL:** `/dub/upload` entra en el paso 11.
  - **A6. Red privada** (paso 2): rechazada salvo que el Usuario lo permita con una variable de entorno (`private_url_imports_allowed`).
- **Excepciones:** cada una termina en un evento `error` con su clase, su explicación y qué hacer (§5.1).
  - **E1. Comprobación antibots** (#2034): no se reintenta ni se cambia de cliente; remite a adjuntar un `cookies.txt` o a descargar el video a mano.
  - **E2. DRM con todos los clientes:** `VIDEO_DRM_PROTECTED`.
  - **E3. URL no soportada:** `UNSUPPORTED_VIDEO_URL`.
  - **E4. El sistema rechaza la escritura o el disco está lleno** (#1225): el mensaje nombra la carpeta y el espacio libre, y dice que reintentar no sirve.
  - **E5. Red agotada tras A2:** `VIDEO_DOWNLOAD_NETWORK`, con la indicación "Just retry".
  - **E6. yt-dlp no instalado** (paso 3): error con la orden de instalación.
- **Garantías:**
  - **De éxito:** el video descargado y reproducible, y el audio preparado.
  - **Mínima:** no quedan archivos `original.*` a medio escribir ni la exportación de cookies; el error tiene clase y mensaje legible.
- **Evidencia:** `backend/api/routers/dub_core.py` (`dub_ingest_url`, `_stage_cookie_export`); `backend/services/dub_pipeline.py` (`ingest_pipeline`, `yt_download_sync`, `_is_transient_download_error`, `_is_forbidden_download_error`); `backend/core/url_safety.py`; pruebas `tests/test_dub_download_*.py`, `tests/test_yt_bot_check_2034.py`.

### VS-UC-02 Cancelar una importación o un doblaje

- **Objetivo:** el trabajo deja de ejecutarse, sin procesos vivos y sin la exportación de cookies.
- **Disparador:** el Usuario cancela, o se cierra el canal de eventos de la tarea.
- **Flujo básico** (`dub_core.dub_abort`, `dub_pipeline._stop_download`):
  1. Marca el trabajo como abortado **antes** de terminar sus procesos, para que el reintento con otro codificador no lo confunda con un fallo.
  2. Termina los subprocesos del trabajo y cancela la tarea.
  3. La descarga en curso ve la marca en su siguiente hook de progreso o de postprocesado y lanza `DownloadCancelled`.
  4. Espera a que la descarga se detenga, con un plazo; luego borra los parciales y las cookies.
- **Alternativos:**
  - **A1. La tarea ya había terminado:** la cancelación es idempotente.
  - **A2. La descarga no se detiene a tiempo:** lo registra y sigue.
- **Excepción E1:** si la cancelación falla, deshace la marca (el trabajo sigue reintentable) y responde `503`.
- **Evidencia:** `tests/test_dub_download_cancel.py`.

### VS-UC-03 Buscar clips en YouTube

- **Objetivo:** una lista de videos que coinciden con una búsqueda, para elegir una voz de referencia.
- **Flujo:** `yt-dlp --dump-json --remote-components ejs:github -- ytsearchN:<consulta>`; lee una línea JSON por resultado y descarta las que no son válidas.
- **Excepciones:** el error de yt-dlp se devuelve como `500`; si yt-dlp falta, el mensaje lo dice.
- **Nota:** pide los scripts de los retos de JavaScript (`ejs:github`), pero ningún archivo del repositorio declara un runtime de JavaScript (deno). Sin uno en el sistema, esos retos no se pueden resolver.
- **Evidencia:** `gallery.search_youtube`.

### VS-UC-04 Descargar un fragmento de voz de un video

- **Objetivo:** un clip de voz de 1 a 30 s, recortado de un video, guardado en la galería.
- **Flujo básico:**
  1. Valida la URL (como VS-UC-01, paso 2).
  2. Descarga solo el audio (`-f bestaudio`) con el descargador nativo, sin playlist, bajo la misma protección de red.
  3. Recorta el fragmento con ffmpeg en el equipo. Usar `--download-sections` le pasaría la URL a ffmpeg, fuera de esa protección.
  4. Guarda el clip y su ficha.
- **Excepciones:**
  - inicio posterior al final del video;
  - archivo no encontrado;
  - error de yt-dlp;
  - URL rechazada por la política de red.
- **Garantía mínima:** borra los archivos intermedios.
- **Evidencia:** `gallery.download_youtube_clip`, `_cut_local_clip`.

### VS-UC-05 a VS-UC-09 Cola de doblaje por lotes

Una cola en memoria que procesa los trabajos uno a uno. Los trabajos se guardan en SQLite como historial, pero la cola **arranca vacía tras un reinicio**: es intencional, porque los trabajos de GPU no se pueden reanudar con seguridad (`backend/api/routers/batch.py`). Las entradas son **archivos subidos**, no URLs. Los estados son `queued`, `running`, `done`, `failed` y `cancelled`.

| Caso de uso | Flujo | Evidencia |
|---|---|---|
| **VS-UC-05 Encolar un doblaje** | Sube el video, los idiomas, la voz y el proveedor de traducción. Rechaza los manifiestos de listas (`is_manifest_file`) para que ffmpeg no siga sus URLs. Devuelve el id y la posición en la cola | `enqueue_batch_job` |
| **VS-UC-06 Cancelar un trabajo** | Uno terminado responde `already`. Uno en curso pasa a `cancelled`, pero no se puede reintentar hasta que se detenga (`retry_ready`) | `cancel_batch_job` |
| **VS-UC-07 Reintentar un trabajo** | Solo `failed` o `cancelled`, y no mientras se detiene. Antes comprueba que el proveedor de traducción y los paquetes de idioma estén listos. Borra las salidas y vuelve a `queued` con `attempts + 1` | `retry_batch_job`, `_admit_retry` |
| **VS-UC-08 Listar y ver trabajos** | Filtros `active` (`queued` y `running`) y `retryable` (`failed` y `cancelled`) | `list_batch_jobs`, `get_batch_job` |
| **VS-UC-09 Borrar un trabajo o el historial** | Nunca borra archivos de un trabajo en cola, en curso, deteniéndose o con un reintento en marcha (#2547). Borra todos los archivos propios del trabajo. El historial de doblajes se borra uno a uno o entero | `delete_batch_job`; `dub_core` `/dub/history` |

### VS-UC-10 Recuperar tras un reinicio

- **Disparador:** el backend arranca.
- **Flujo:** marca como `failed` todo trabajo `pending` o `running`, con el mensaje "Job was interrupted by a server restart. Re-run from the task's project to continue.". No reanuda nada.
- **Evidencia:** `core/job_store.sweep_orphans_on_startup`.

### VS-UC-11 Gestionar ffmpeg y ffprobe

- **Objetivo:** que la app tenga un ffmpeg utilizable.
- **Flujos** (`media_tools`):
  - ver el estado y el origen de cada herramienta: incluida, del sistema, personalizada o de `imageio`;
  - descargar o reparar la versión incluida: commit fijado de `zackees/ffmpeg_bins`, con SHA-256 y tamaño por plataforma;
  - usar una ruta personalizada (validada);
  - usar la del sistema;
  - volver a la incluida.
- **Evidencia:** `backend/services/media_tools.py` (`acquire_bundled`, `set_custom_path`, `use_system`, `restore_bundled`).

### VS-UC-12 Actualizar yt-dlp y volver a la versión probada

- **Objetivo:** arreglar las descargas cuando un sitio cambia, sin esperar a una versión nueva de la app.
- **Flujo básico:**
  1. El Usuario pide actualizar.
  2. La app lee de PyPI la última versión y su rueda universal.
  3. La descarga y verifica el SHA-256 que publica PyPI.
  4. Extrae solo el paquete `yt_dlp` en una carpeta propia (*overlay*) y lo instala de forma atómica.
  5. Al siguiente arranque, esa carpeta va delante de la versión fijada en el lock.
- **Alternativo A1. Volver a la versión probada:** la primera actualización guarda la versión del lock como base, y "Restore tested version" vuelve a ella.
- **Evidencia:** `media_tools.update_ytdlp`, `_do_update_ytdlp`, `activate_ytdlp_overlay`.

### VS-UC-13 Configurar el entorno (proxy y tokens)

- **Flujo:**
  - Las variables se guardan en un archivo del usuario (`~/.config/omnivoice/env`, permisos 0600) y se cargan al arrancar.
  - yt-dlp no recibe un proxy explícito: usa el de esas variables (`HTTPS_PROXY`, `ALL_PROXY`).
  - Dos problemas tienen su propia clase: un proxy SOCKS sin la librería necesaria, y un proxy de empresa que intercepta HTTPS.
- **Evidencia:** `core/user_env.py`; `core/failure.py` (`SOCKS_PROXY_SUPPORT_MISSING`, `SSL_HANDSHAKE_FAILURE`).

### VS-UC-14 Autodiagnóstico

- **Disparador:** *Settings → About → Run self-check*, o `python main.py --diagnose`.
- **Flujo:** revisa Python, el dispositivo, ffmpeg, el token de Hugging Face, el disco, los permisos de la carpeta de datos, la RAM y los motores. Si se pide, revisa también el acceso de red al hub.
  - Cada comprobación es `ok`, `warn` (degradado pero usable; por ejemplo, el hub no responde) o `fail` (la app no puede trabajar), con una indicación de qué hacer.
  - El texto pasa por una limpieza de datos sensibles (`core.scrub`).
- **Evidencia:** `core/diagnose.py`.

### VS-UC-15 Guardar un paquete de diagnóstico

- **Disparador:** *Save diagnostic bundle*.
- **Flujo:** genera un `.zip` con la versión y la plataforma, el autodiagnóstico, el diario de errores clasificados, los tiempos recientes, las últimas 500 líneas del log y las últimas 200 del log de fallos. Todo pasa por la limpieza de datos sensibles. Lo guarda en la carpeta de salidas y la abre.
- **Evidencia:** `core/diagnostic_bundle.py`.

## 5. Flujos transversales

### 5.1 Clasificar un fallo e informar qué hacer (incluido por VS-UC-01 a VS-UC-04, VS-UC-07 y VS-UC-10)

- **Una taxonomía central:** `core/failure.py`, función `classify(texto)`.
  - Reconoce cada clase por firmas en el texto y, para el disco, por `errno` o `winerror` en toda la cadena de causas de la excepción (`__cause__`, `__context__`).
  - Cada clase tiene una indicación (`_HINTS`) que dice **si reintentar sirve**.
  - El evento de fallo (`build_failure`) nunca queda vacío y se limpia de tokens y rutas personales.
- **Orden de las comprobaciones:** primero la clase más específica.
  - `UNSUPPORTED_VIDEO_URL` va antes que la red.
  - El bloqueo antibots va antes que DRM y que la red, para que nunca se reintente.
- **Lo que no reconoce:** el límite de peticiones de YouTube ("This content isn't available, try again later") ni el captcha.

| Clase | Firma | ¿Reintentar sirve? |
|---|---|---|
| `VIDEO_DOWNLOAD_BOT_CHECK` | "not a bot" con "sign in" o "cookies" (los dos apóstrofos) | No: cookies o descarga manual |
| `VIDEO_DRM_PROTECTED` | "drm protected" | Ya se probaron otros clientes |
| `VIDEO_DOWNLOAD_NETWORK` | "broken pipe", "connection reset", "timed out", "unable to download video"… | Sí ("Just retry") |
| `VIDEO_DOWNLOAD_OS_ERROR` | El sistema rechaza la escritura en la descarga | No: disco, permisos, antivirus o sincronización en la nube |
| `DISK_FULL` | `ENOSPC`, `EDQUOT`, `winerror` 112 y 39, "no space left" | No: "retrying with backoff only delays the message" |
| `TLS_CONNECTION_DROPPED`, `SSL_HANDSHAKE_FAILURE`, `SOCKS_PROXY_SUPPORT_MISSING` | Errores de TLS o de proxy | Depende de la clase |

### 5.2 Política de reintentos

| Situación | Política | Evidencia |
|---|---|---|
| Red (descarga) | 2 reintentos, 2 s y 4 s, borrando antes los parciales | `yt_download_sync` |
| 403 o DRM | Hasta 3 clientes de YouTube | `_YT_PLAYER_CLIENTS` |
| Bloqueo antibots, disco lleno, rechazo de escritura | Ninguno | `test_yt_bot_check_2034.py`, `failure.is_disk_full_error` |
| Reintentos internos de yt-dlp | `retries` 10, `fragment_retries` 10, `extractor_retries` 5, `socket_timeout` 30 | `ydl_opts` |
| HTTP 429 de otros servicios (traducción) | Un solo reintento si el servidor pide esperar poco; un segundo 429 se propaga | `services/translator.py` |
| Archivo bloqueado un momento por el antivirus o el indexador | Unos 4 s en total (0,1 a 2 s) | `core/fs_retry.py` |

**Ninguna espera larga.** Lo que reintentar no puede arreglar se informa en el acto.

### 5.3 Resistencia en Windows

- **Árbol de procesos:** Job Object con `KILL_ON_JOB_CLOSE` y vigilancia del proceso padre (`core/contained_subprocess.py`, `core/parent_liveness.py`).
- **Sin ventanas de consola:** `CREATE_NO_WINDOW` en todo `subprocess.Popen` (`core/win_subprocess.py`).
- **yt-dlp sin depender de stdout ni stderr:** `noprogress` y `logger` (`tests/test_dub_download_stdio.py`).
- **Fecha del archivo:** desactivan `updatetime` por un error 22 en Windows (#642). En yt-dlp 2026.11.23 ya está desactivada por defecto y el cambio de fecha se ignora si falla (`downloader/common.py`, `fragment.py`).

## 6. Trazabilidad con nuestros casos de uso

| VoiceStudio | queued-media-downloader | Relación |
|---|---|---|
| VS-UC-01 Importar un video desde una URL | UC-02 Encolar contenido + UC-03 Descargar un contenido | Mismo objetivo. Nosotros persistimos la cola, admitimos playlists, reanudamos desde los parciales y reclamamos el nombre final; ellos reintentan borrando los parciales |
| VS-UC-01 A1 (cookies) | — | Decisión D-1. Su forma, explícita y de un solo uso, es el modelo si se adopta |
| VS-UC-01 A2 (red) | UC-12 (propuesto) | Ellos reintentan poco y sin esperar; refuerza "detener sin gastar" |
| VS-UC-01 A3 (cambio de cliente) | — | No se adopta: `android` exige PO Token (wiki de yt-dlp); nuestros clientes por defecto no lo necesitan |
| VS-UC-01 E1 (antibots) | UC-11 (propuesto), BR-01 | Mismo diagnóstico; ellos no esperan. BR-01 cubre además el límite de peticiones y el captcha, que ellos no reconocen |
| VS-UC-01 E4 (disco) | UC-13 (propuesto), BR-08 | Su comprobación previa del destino y las causas encadenadas mejoran BR-08 |
| VS-UC-01 A6 (red privada) | — | No aplica: nuestro programa es local y el usuario escribe sus propias URLs |
| VS-UC-02 Cancelar | UC-05 Cancelar un job | Mismo mecanismo (`DownloadCancelled` en los hooks); nosotros conservamos los parciales |
| VS-UC-03, VS-UC-04 Galería | — | Fuera de alcance (no es descargar contenidos completos) |
| VS-UC-05 a VS-UC-09 Cola por lotes | UC-02, UC-05, UC-07, UC-08, UC-09, UC-10 | Paralelo directo; sus `retry_ready` y la regla de no borrar mientras algo se detiene coinciden con nuestro UC-05 A8 y la restricción de UC-10 |
| VS-UC-10 Recuperar tras un reinicio | UC-06 Recuperar la cola y reanudar | Ellos fallan los trabajos interrumpidos; nosotros los reanudamos |
| VS-UC-11 Gestionar ffmpeg | UC-01 Instalar y verificar | Nosotros incluimos ffmpeg con Git LFS y verificamos su SHA-256; ellos lo descargan con SHA-256 y aceptan una ruta personalizada |
| VS-UC-12 Actualizar yt-dlp | SUP-S01, ADR-0002, riesgo R-20 | Diferencia de fondo: ellos dejan al usuario instalar la última versión; nosotros la fijamos. Se anota en R-20 |
| VS-UC-13 Entorno (proxy) | D-7 (propuesta) | Confirma: proxy del entorno, con diagnóstico de sus fallos típicos |
| VS-UC-14 Autodiagnóstico | UC-01 (`diagnose`), UC-01 A9 (propuesto) | Su resultado `warn` para la red confirma la forma de UC-01 A9 |
| VS-UC-15 Paquete de diagnóstico | VUC-07 (para la validación) | En el producto no tenemos un paquete para reportar fallos; queda como candidato de prioridad baja |
| §5.1 Taxonomía de fallos con su indicación | `failure_classifier`, SUP-U01 | Añadir a cada motivo si reintentar sirve |

## 7. Lo que tenemos y VoiceStudio no

- Una cola persistente que sobrevive a un cierre y reanuda desde los parciales (UC-06, SUP-R01).
- Playlists y canales con iteración perezosa y duplicados por media key (UC-04, ADR-0009).
- Propiedad de los nombres finales mediante reclamaciones (ADR-0030).
- yt-dlp fijado con pruebas de contrato y un procedimiento de actualización (SUP-S01).
- deno y yt-dlp-ejs incluidos para los retos de JavaScript de YouTube.
- El límite de peticiones y el captcha reconocidos (BR-01, propuesto) y un ritmo de peticiones por sitio (BR-02, propuesto).

## 8. Lecciones para este proyecto

| Lección | Destino | Estado |
|---|---|---|
| Detener e informar, sin esperas largas, ante el bloqueo, el disco lleno o la red agotada | UC-11 a UC-13, ADR-0031 | Refuerza el cambio pendiente de decisión |
| Cada motivo de fallo dice si reintentar sirve | SUP-U01, BR-01, BR-05, BR-08 | Propuesta |
| Reconocer el bloqueo con los dos apóstrofos | Prueba de contrato de T52 | Propuesta |
| Disco lleno por `errno` o `winerror` en toda la cadena de causas, y comprobación previa del destino | BR-08, T55 | Propuesta |
| Cookies explícitas y de un solo uso, si se adoptan | D-1 | Pendiente |
| Proxy del entorno con diagnóstico | D-7 | Pendiente |
| Separar actor y juez en la validación (arnés `tests/probe`: "No LLM ever sits on the verdict path") | VUC-04 | Propuesta |
| Pruebas de regresión con el texto literal del error reportado | Proceso de desarrollo | Propuesta |
| Actualizar yt-dlp desde la app | R-20 | Solo se anota |

## Fuentes

Todas en el commit indicado del repositorio clonado:
- **Documentación:** `docs/features.yaml`, `docs/feature-catalog.md`, `docs/electron-dubbing.md`, `tests/probe/README.md`.
- **Routers** (`backend/api/routers/`): `dub_core.py`, `gallery.py`, `batch.py`, `media_tools.py`.
- **Servicios** (`backend/services/`): `dub_pipeline.py`, `media_tools.py`, `translator.py`.
- **Núcleo** (`backend/core/`): `failure.py`, `url_safety.py`, `job_store.py`, `job_queue.py`, `fs_retry.py`, `user_env.py`, `diagnose.py`, `diagnostic_bundle.py`, `win_subprocess.py`, `contained_subprocess.py`, `parent_liveness.py`.
- **Pruebas** (`tests/`):
  - descarga: `test_dub_download_retry.py`, `test_dub_download_403.py`, `test_dub_download_cancel.py`, `test_dub_download_os_error.py`, `test_dub_download_stdio.py`, `test_dub_download_mtime.py`, `test_dub_download_ffmpeg_location.py`;
  - bloqueos y credenciales: `test_yt_drm_escalation.py`, `test_yt_bot_check_2034.py`, `test_youtube_cookie_import.py`.
- **Dependencias:** `pyproject.toml` (`yt-dlp>=2026.7.4`) y `uv.lock` (yt-dlp 2026.8.19; sin yt-dlp-ejs ni deno).
