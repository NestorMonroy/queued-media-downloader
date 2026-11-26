# Análisis de requisitos: continuidad, condiciones externas y referencias

- **Fase RUP:** Elaboración (consolidación del modelo de requisitos tras la campaña T42)
- **Versión:** 4.0 (2026-11-26; alcance de 26 casos de uso aceptado por el Responsable; resolución de D-1 a D-21, §9; contratos, §13.11 a §13.19; impacto en la arquitectura, §14). 3.3: reconciliación de exclusiones y contratos transversales. 3.2 (2026-11-26; condiciones de almacenamiento separadas en UC-17 y análisis del acceso con proxy y cookies). 3.1 (añade YTDownload-2026 y VoiceBlueprintPro). 3.0 (2026-11-26). La versión 2.0 se titulaba «funcionamiento sin vigilancia y validación sin esperas»; esta integra el análisis de los proyectos de referencia en el modelo canónico y deja abiertas las decisiones.
- **Responsabilidad:** razonamiento y evidencia del modelo de requisitos. Los requisitos están en sus artefactos: [modelo de casos de uso](use-case-model.md), [reglas de negocio](business-rules.md), [especificación complementaria](supplementary-specification.md), [catálogo de condiciones de fallo](failure-conditions.md) y [modelo de validación](../process/validation-use-case-model.md).
- **Técnicas (BABOK v3):** ver §5.2.

---

## 1. Necesidad (6.1)

| | |
|---|---|
| **El problema de** | una cola que no reacciona a lo que pasa fuera de ella (el sitio bloquea, falta la red, se llena el disco), y una validación en Windows que depende de esperas y de pasos manuales |
| **afecta a** | el User, que deja la cola trabajando sin vigilarla, y al Evaluador, que valida cada commit en Windows |
| **cuyo impacto es** | jobs sanos marcados `FAILED` en segundos; peticiones a un sitio que ya bloquea; trabajo manual para notar, esperar y reintentar; y, en la campaña, la mitad del tiempo del Evaluador esperando instrucciones (§2.2) |
| **una solución exitosa** | preserva los jobs cuando el sitio o el entorno no responden, no insiste ante quien restringe, informa y continúa según una política decidida; y una validación que ejecuta y comprueba cada bloque sin que el Evaluador espere a nadie |

**Restricción del Responsable (2026-11-26):** no depender de PO Tokens.

## 2. Estado actual (6.1)

### 2.1 Evidencia del producto

| Momento (2026-11-25) | Suceso externo | Respuesta actual de la cola |
|---|---|---|
| 22:24, paso 5.2 | El equipo perdió la resolución de nombres (`getaddrinfo failed`, 11001) | 8 jobs `FAILED` con `NETWORK` en segundos y uno `UNKNOWN` (T42-D7); `run` siguió enviando jobs hasta vaciar la cola |
| 23:27, paso 5.7 | Otro programa retuvo la base de datos | `run` terminaba a mitad de la cola (T42-D12, ya corregido) |
| 23:36, paso 5.7 | YouTube respondió `Sign in to confirm you're not a bot` a toda petición | Cada job falló en 1 o 2 s con `UNAVAILABLE`, gastando su intento |

Entre las 22:23 y las 23:36, los logs de las colas registran 93 extracciones de YouTube (81 videos y 12 playlists), más las 4 pruebas `network`. Es menos que el límite de las sesiones de invitado que documenta yt-dlp (unos 300 videos por hora; página *Extractors* de su wiki). El bloqueo, por tanto, no depende solo del número de peticiones.

### 2.2 Mapa de flujo de valor de la sesión de validación (10.34)

La sesión del Evaluador fue el 2026-11-25, de 22:18 a 23:51 (unos 92 min).
- **De dónde salen los tiempos:** la consola del Evaluador muestra, en cada prompt, la hora y el tiempo transcurrido desde el anterior, con un margen de un minuto. Las esperas son el tiempo entre el último comando de un mensaje del Evaluador y el primero del siguiente; incluyen leer la instrucción y escribirla.
- **Clases:** valor añadido (VA), necesaria para el negocio (BVA) y sin valor añadido (NVA).

| Actividad | Min | Clase | Desperdicio (Lean) |
|---|---|---|---|
| Suites (paso 3) | 11,3 | VA | — |
| Pasos 5.2 a 5.7 con resultados válidos, incluidos los que encontraron T42-D10 y T42-D12 | 25 | VA | — |
| Preparar la ejecución, las colas, la segunda ventana y la evidencia | 5 | BVA | — |
| **Esperar la siguiente instrucción del analista** (9 esperas; la mayor, de 13 min, de 22:52 a 23:05) | **47,5** | NVA | Espera |
| Pasos repetidos por defectos del guion (5.6 sin cola, 5.7, 5.7-r2, `purge`) | 2,5 | NVA | Defectos y reproceso |
| Arranque fallido por un comando incompleto del analista (faltaba `git fetch`) | 0,5 | NVA | Defectos |
| Comprobar a mano si YouTube responde | 0,7 | NVA | Espera |

**Resultado:** un 39 % del tiempo es de valor añadido y un 51 %, espera.
- **El desperdicio dominante** no viene de la red ni del sitio: es el traspaso paso a paso entre el Evaluador y el analista. Cada resultado se pega en la conversación, se interpreta a mano y vuelve como una instrucción nueva.
- **Una dependencia innecesaria:** los pasos 6 a 12 prueban procesos, cierres y archivos, pero descargan de YouTube, así que heredan sus bloqueos y los de la red.

## 3. Causa raíz (10.40)

### 3.1 Espina de pescado

```mermaid
---
config:
  theme: base
  darkMode: true
  themeVariables:
    background:         "#0f172a"
    primaryColor:       "#1e293b"
    primaryTextColor:   "#f1f5f9"
    primaryBorderColor: "#94a3b8"
    lineColor:          "#cbd5e1"
    secondaryColor:     "#334155"
    tertiaryColor:      "#1e3a8a"
    noteBkgColor:       "#1e3a8a"
    noteTextColor:      "#f1f5f9"
---
ishikawa-beta
    Jobs sanos FAILED y validación con esperas
    Procesos
        Cada error se trata como fallo del job
        Run envía el siguiente job sin pausa
        Validación paso a paso con traspasos
    Herramientas
        yt-dlp no tiene excepción propia para el bloqueo
        Resultados esperados del guion en prosa
        La campaña descarga de YouTube para probar procesos
    Requisitos
        Casos de uso sin sucesos externos
        Sin reglas para aplazar o reintentar
    Entorno
        Sitio que bloquea sesiones de invitado
        Red doméstica inestable
        Disco que se llena con playlists grandes
```

### 3.2 Cinco porqués

| Problema | Porqués | Causa raíz |
|---|---|---|
| Todos los jobs pendientes acaban `FAILED` tras un corte o un bloqueo | 1. `run` envía el siguiente job, que también falla. 2. `run` trata cada error como un fallo del job. 3. La clasificación de fallos solo tiene motivos por job (`FailureReason`); no existe una condición del entorno que comparten todos los jobs. 4. UC-03 A2 modeló los fallos como sucesos de un job. 5. Los casos de uso se identificaron por los objetivos del User, no por los sucesos externos (BABOK 10.47 admite casos de uso iniciados por un suceso externo) | **Faltó la lista de sucesos externos** al identificar los casos de uso |
| El Evaluador espera la mitad de la sesión | 1. Tras cada paso espera la siguiente instrucción. 2. El resultado se interpreta a mano en la conversación. 3. El guion describe los resultados esperados en prosa y nada los comprueba. 4. La campaña se diseñó como un guion manual (ADR-0021: sin CI; comportamientos que solo existen en Windows). 5. La herramienta de validación no se trató como una solución con sus propios casos de uso | **La validación no tiene un oráculo automático**, y sus pasos dependen de YouTube y de la red aunque no los prueben |

## 4. Identificación sistemática de casos de uso

### 4.1 Lista de actores y objetivos

| Actor | Objetivo | Cubierto por | Clasificación |
|---|---|---|---|
| User | Instalar y verificar | UC-01 | Existente; A10 y A11 propuestos |
| User | Saber qué contiene una URL antes de encolarla | — | **UC-15 nuevo** |
| User | Poner contenidos en la cola, con sus opciones | UC-02 | Existente; A5 a A8 propuestos (mismo objetivo) |
| User | Que la cola se descargue sin vigilarla | UC-03, UC-04 | Existente; extendido por UC-11 |
| User | Cancelar, recuperar, reintentar, listar, ver, purgar | UC-05 a UC-10 | Existente |
| User | Dejar libre la conexión o el equipo un rato sin perder la cola | — | **UC-14** (propuesto en la versión 2.0; reformulado por la necesidad) |
| User | Reportar un problema con todo lo necesario | — | **UC-16 nuevo** |
| User | Descargar sin saturar la conexión | — | Requisito no funcional (SUP-P06): una configuración, sin interacción propia |
| User | Usar su cuenta del sitio o un proxy | — | **UC-19** (condicionado a D-1 y D-7) |
| User | Actualizar yt-dlp sin esperar una versión del programa | Procedimiento SUP-S01 | **UC-27** (condicionado a D-8) |
| User | Descargar solo en ciertas horas sin estar presente | — | **UC-21** (revisado en §12: el Programador de tareas no cubre las ventanas) |
| User | Enterarse de los sucesos sin vigilar la consola | — | **UC-28** (revisado en §12) |
| User | Reutilizar preferencias de descarga | — | **UC-18** |
| User | Ver, cambiar y trasladar la configuración | — | **UC-20** |
| User | Trasladar o conservar la cola | — | **UC-22**, **UC-23** |
| User | Obtener solo la información complementaria | — | **UC-24** |
| User | Administrar y verificar lo descargado | — | **UC-25**, **UC-26** |
| Programa cliente | Usar el producto sin interpretar texto | Todos | SUP-I01; canal según D-17 |
| Mantenedor | Actualizar yt-dlp cuando un sitio cambia | Procedimiento SUP-S01 | Proceso de desarrollo |
| Evaluador | Validar un commit en Windows | VUC-01 a VUC-08 | [Modelo de validación](../process/validation-use-case-model.md) |

### 4.2 Lista de sucesos externos y temporales

Cada suceso tiene su fila, con sus atributos, en el [catálogo de condiciones de fallo](failure-conditions.md). Aquí solo se clasifica su destino.

| Suceso | Destino |
|---|---|
| El sitio restringe la sesión (antibots, captcha, límite de peticiones, HTTP 429) | UC-11 A1; BR-01 |
| El equipo pierde la conectividad | UC-11 A2; BR-05 |
| Falla el almacenamiento: espacio, cuota, permisos, carpeta inexistente, unidad ausente, uso compartido | UC-17; BR-08, BR-25 a BR-28 ([catálogo, §3](failure-conditions.md#3-almacenamiento-y-archivos)) |
| Fallo transitorio con un host (5xx, timeout) | UC-03 A15; BR-07 (divergencia R-24) |
| El equipo se suspende | SUP-R08; al despertar, UC-11 A2 |
| Cierre o corte de luz | UC-06 |
| Cierre entre el final de la descarga y el registro | UC-06 A4 y A11 (propuesto); R-25 |
| Otro programa retiene la base de datos | UC-03 A10 (corregido, T42-D12) |
| Un antivirus bloquea un archivo un instante | `file_access_retries` (vigente) |
| El sitio cambia y el extractor falla | UC-03 A3, SUP-S01; D-8 |
| YouTube exige PO Token a los clientes por defecto | R-20; BR-12 |
| Un contenido pide una cuenta | UC-03 A2; UC-11 E2 |
| Una transmisión en directo o programada | UC-03 E1; D-10; R-26 |

### 4.3 Consolidación de los casos de uso propuestos en la versión 2.0

La versión 2.0 propuso UC-11 (esperar a que el sitio levante un bloqueo), UC-12 (esperar a la red), UC-13 (esperar espacio en disco) y UC-14 (pausar y continuar). Sus nombres describían una solución, esperar, y no la necesidad. Las referencias no esperan (§6) y eso tampoco prueba que esperar sea incorrecto: la política es una decisión (D-2).

| Antes | Necesidad | Ahora |
|---|---|---|
| UC-11 Esperar a que el sitio levante un bloqueo | Preservar los jobs ante una restricción externa | UC-11 A1 |
| UC-12 Esperar a la red | Administrar las interrupciones de conectividad | UC-11 A2 |
| UC-13 Esperar espacio en disco | Preservar el trabajo ante fallos de almacenamiento | UC-17 (nuevo identificador) |
| UC-14 Pausar y continuar la cola | Controlar temporalmente la ejecución | UC-14, con detención ordenada (A2) |

UC-12 y UC-13 se retiran y sus identificadores no se reutilizan.

**Revisión del almacenamiento (2026-11-26).** Al consolidar, el almacenamiento quedó como un escenario de UC-11 con una sola regla de espacio mínimo. Esa reducción no se sostiene:
- las condiciones tienen naturalezas distintas: espacio, cuota, permisos, disponibilidad de la unidad y uso compartido. Solo algunas se resuelven esperando; otras requieren una acción del User ([catálogo, §3.1](failure-conditions.md#31-condiciones));
- una comprobación previa no garantiza la descarga: la condición puede aparecer a mitad del job, así que hacen falta escenarios preventivos y reactivos;
- yt-dlp pierde o esconde el error original en varios caminos, y la identificación debe recorrer toda la cadena de causas (§3.2 del catálogo, R-28).

El almacenamiento vuelve a tener su propio caso de uso, UC-17, con identificador nuevo. UC-11 conserva el sitio y la conectividad, y los dos comparten el aplazamiento (BR-04) y la política de continuidad (D-2). Los tres primeros compartían actor, disparador (un suceso externo durante `run`), flujo y garantías; su diferencia es la regla de reconocimiento y el alcance, que BABOK 10.47 modela como escenarios de un mismo caso de uso.

## 5. Referencias analizadas y técnicas

### 5.1 Referencias

Las referencias solo aportan evidencia. No son dependencias del producto, no se modifican y no se copia su código (licencias incompatibles con The Unlicense: Seal es GPL-3.0 y VoiceStudio, AGPL-3.0).

| Proyecto | Versión o commit | Licencia | Alcance analizado | Limitaciones |
|---|---|---|---|---|
| queued-media-downloader | `main` en `14bd247` | Unlicense | Todo el código y los documentos | — |
| yt-dlp | 2026.11.23 (la fijada, sdist en `/tmp/ytdlp-new`); 2026.10.26 en el espacio de análisis | Unlicense | `options.py` y `__init__.py` (valores de la línea de comandos), `YoutubeDL.py` (valores de la librería), `utils/_utils.py` (`RetryManager`), `extractor/youtube/` (clientes, restricciones), `networking/` (proxy, timeouts), `postprocessor/` | Solo el código fuente; no se ejecutó contra sitios reales |
| Seal | `5a4f5fb` (2026-11-25), versionCode 200_000_150 | GPL-3.0 | Descarga, cola (`download/DownloaderV2.kt`), preferencias (`util/PreferenceUtil.kt`, `util/DownloadUtil.kt`), formatos y playlists (`ui/page/downloadv2/configure/`), historial, actualización (`util/UpdateUtil.kt`), cookies, comandos personalizados, errores | Aplicación Android: lo propio de Android (tarjeta SD, red medida) solo se usa como evidencia de la necesidad |
| VoiceStudio | `d9061408` (2026-11-26) | AGPL-3.0 | Importación desde URL (`services/dub_pipeline.py`), cola por lotes (`api/routers/batch.py`), fallos (`core/failure.py`), herramientas de medios, entorno, autodiagnóstico, paquete de diagnóstico, resistencia en Windows, arnés de pruebas | Solo el dominio compartido; el procesamiento de voz e IA queda fuera |
| YTDownload-2026 | `0abda8e` (2026-07-02), 33 commits; yt-dlp 2026.2.4 en su `uv.lock` | **Sin licencia declarada** (todos los derechos reservados): solo se toman ideas | Toda la aplicación: `infrastructure/ytdlp_service.py`, `application/download_coordinator.py`, `application/command_api.py`, modelos (`domain/models/`), CLI (`interfaces/cli/root.py`), herramientas MCP (`infrastructure/mcp/tools/`), `docs/` (guía de descarga de YouTube en 2026: proxy, cuentas, cookies, subtítulos, playlists) | Interfaz gráfica (PySide6) leída solo por sus opciones; documentación en ruso |
| VoiceBlueprintPro | `e9a2a63` (2026-11-22), 89 commits; yt-dlp 2026.8.19 | AGPL-3.0 | Derivado de VoiceStudio (separado el 2026-11-09, según su historial y `NOTICE`). Se comparó, archivo por archivo, con VoiceStudio `d9061408` en el dominio compartido: importación desde URL, fallos, entorno, herramientas de medios, cola por lotes, autodiagnóstico, asistente de instalación (`api/routers/setup/`) | Su canal de importación es una versión anterior a la de VoiceStudio; el resto (voz, IA, móvil) queda fuera del dominio |
| Kannagi (yt-dlp-gui) | Sin Git ni versión declarada, en `upstream/source/yt-dlp-gui-kannagi` | MIT | `Wrappers/DLP.cs`, `Wrappers/FFMPEG.cs`, `ViewModels/Main.cs`, `Models/Config.cs`, `Models/Cookies.cs`, `Views/Release.xaml.cs` | Sin versión: los hallazgos no se pueden fechar |
| FFmpeg | Código: checkout parcial de `master` en `329157f5` (2026-11-22); binarios: n9.0.2-39 LGPL compartido, en `vendor/ffmpeg/` | LGPL | Contratos que usa el producto: unión de video y audio, extracción de audio, `ffprobe` | El checkout solo tiene los registros de códecs y formatos y los Makefiles; los contratos se verificaron con los binarios incluidos y la documentación de yt-dlp |
| BABOK v3 | Copia entregada por el Responsable | IIBA | Capítulos 6, 7 y 10 | — |

### 5.2 Técnicas aplicadas

| Técnica (BABOK v3) | Aporte |
|---|---|
| 10.4 Benchmarking and Market Analysis | §6: cada capacidad de las referencias, con su destino |
| 10.18 Document Analysis | Lectura del código y la documentación de las referencias y de la wiki de yt-dlp |
| 10.22 Functional Decomposition | Inventario de capacidades de cada referencia antes de clasificarlas |
| 10.24 Interface Analysis | §7.1: parámetros de la librería de yt-dlp frente a su línea de comandos |
| 10.9 Business Rules Analysis | Separación de reglas, parámetros y decisiones en el [catálogo](business-rules.md) |
| 10.16 Decision Modelling | §9 |
| 10.40 Root Cause Analysis | §3 |
| 10.34 Process Analysis | §2.2 (mapa de flujo de valor) |
| 10.44 State Modelling | Estados de los jobs ante cada condición ([catálogo de condiciones](failure-conditions.md)) |
| 10.47 Use Cases and Scenarios | UC-11 consolidado, UC-14 a UC-16 y el formato común de los casos de uso |
| 10.30 Non-Functional Requirements Analysis | Especificación complementaria 2.0 |
| 10.38 Risk Analysis | R-24 a R-27 |
| 10.1 Acceptance and Evaluation Criteria | Criterios de aceptación de cada caso de uso |
| 10.33 Prioritization | §8.2 |
| 10.41 Scope Modelling | Exclusiones (§6.3) y [modelo de casos de uso](use-case-model.md) |
| 10.6 Business Capability Analysis | §6: capacidades agrupadas por área |
| 10.21 Glossary | [Vocabulario](../design/00-vocabulary.md), §1.0 |

## 6. Hallazgos de las referencias y su incorporación

Cada hallazgo se cualifica en una sola categoría y tiene un único destino en el modelo canónico. **Estado** describe nuestro producto: vigente, parcial, propuesto, divergente o excluido. Las referencias se citan como S (Seal), V (VoiceStudio), B (VoiceBlueprintPro), D (YTDownload-2026), K (Kannagi), Y (yt-dlp) y F (FFmpeg). Una fila con varias letras es un requisito propio respaldado por varias referencias.

### 6.1 Capacidades del dominio

| Área | Capacidad | Evidencia | Categoría | Destino | Estado |
|---|---|---|---|---|---|
| Cola | Varias descargas a la vez | S: `MAX_CONCURRENCY = 3` en `DownloaderV2.kt`; D: `max_concurrent` = 2 | UC existente | SUP-P01 (`worker_count`) | Vigente |
| Cola | Fallo restartable, sin perder la tarea | S: estado `Error`; V: `retry_batch_job` | UC existente | UC-07 | Vigente |
| Cola | Reintento solo cuando el trabajo ya se detuvo | V: `retry_ready`, `_admit_retry` | Regla | BR-14 (`CANCELLATION_REQUESTED` no es reintentable) | Vigente |
| Cola | Trabajo interrumpido por un reinicio | S: pasa a `Canceled`; V y B: pasan a `failed` (`sweep_orphans_on_startup`); D: la cola vive en memoria y sus registros quedan `queued` o `downloading` para siempre | UC existente | UC-06, BR-19: nosotros reanudamos | Vigente; mejor que las referencias |
| Cola | No borrar archivos de un trabajo activo | V: `delete_batch_job` (#2547) | Regla | BR-17, BR-18 | Vigente |
| Cola | Pausa, detención | S: cancelar y reanudar tareas | UC nuevo | UC-14 | Propuesto (D-6) |
| Consulta | Información y formatos antes de descargar | S: `fetchInfo`, `FormatPage.kt`; K: Analyze; D: `fetch_info` y el «modo A» de su guía (primero metadatos, después descarga); Y: `-F`, `--dump-json` | UC nuevo | UC-15 | Propuesto |
| Consulta | Elegir entradas de una playlist | S: `PlaylistSelectionPage.kt`; D: guía, §8 («solo 1–20», «5, 7, 9»); Y: `--playlist-items` | Flujo alternativo | UC-02 A6, UC-04 A8 | Propuesto |
| Opciones | Recortar un tramo | S: recortes; K, Y: `--download-sections` | Flujo alternativo | UC-02 A8 | Propuesto, prioridad baja |
| Opciones | Subtítulos, miniatura, metadatos, capítulos | S: `DownloadUtil.kt`; K: incrustar subtítulos, miniatura y capítulos; D: archivos al lado del video (`.info.json`, `.description`, miniatura, subtítulos por idioma, incluidos los automáticos), activados por omisión | Pendiente de cualificación | UC-02 A7 | Pendiente |
| Opciones | Extraer audio y convertirlo | S, K, D, Y: `FFmpegExtractAudio` | UC existente | UC-02 `--audio-only` | Vigente |
| Opciones | Calidad por preajuste (mejor, 1080p, 720p, 480p, 360p, solo audio) | D: `QualityOption` y `_build_format_string`; S y K: selector de calidad | Flujo alternativo | UC-02 A9 | Propuesto |
| Opciones | Opciones por job sobre los valores globales | D: `DownloadCoordinator.add` | UC existente | UC-02: las download options se fijan al encolar | Vigente |
| Opciones | Unir a otro contenedor (mkv) | S, K: remux | Flujo alternativo | UC-02 A14, UC-03 A19 | Propuesto (revisado en §12) |
| Opciones | SponsorBlock, partir por capítulos, `parse-metadata` | S | Flujo alternativo | UC-02 A7, A10 y A11; UC-03 A17 y A18 | Propuesto (revisado en §12) |
| Opciones | Plantillas de comandos personalizados | S: plantillas y su log | Nuevo UC (la necesidad); exclusión (ejecutar comandos) | UC-18 | Propuesto (revisado en §12) |
| Archivos | Plantilla de salida y subcarpetas por playlist | S, K, D (carpeta por playlist y por video, índice con tres cifras), Y | UC existente | UC-03 (plantilla determinista), carpeta de la playlist | Vigente |
| Archivos | Nombres seguros y recortados | S: `restrict-filenames`; Y: `trim_file_name` | UC existente | `max_filename_length` | Vigente |
| Archivos | Archivo de descargas (`--download-archive`) | S: `DOWNLOAD_ARCHIVE` | Decisión arquitectónica | ADR-0012: duplicados por media key | Excluido por ADR |
| Archivos | Fecha del archivo | K: modificada, de subida o de creación; V: desactiva `updatetime` (#642) | Capacidad técnica | Y 2026.11.23 la desactiva por defecto | Vigente (sin cambio de fecha) |
| Archivos | Comprobación previa del destino | V: `ingest_pipeline` (#1225) | Flujo alternativo | UC-17 pasos 2 y 3, A1 a A3; UC-01 A10; BR-28 | Propuesto |
| Archivos | Borrar el registro con su archivo | S: historial; V: `delete_batch_job`; D: `delete_download` con vista previa y confirmación, pero borra la carpeta de salida entera con `shutil.rmtree` | Flujo alternativo | UC-10 A5 | Propuesto (D-11) |
| Fallos | Taxonomía con indicación de si reintentar sirve | V: `core/failure.py` (`_HINTS`) | Requisito suplementario | SUP-U05; catálogo de condiciones | Propuesto |
| Fallos | Antibots nunca se reintenta | V: `test_yt_bot_check_2034.py` | Regla | BR-01, BR-03 | Propuesto |
| Fallos | Límite de peticiones y captcha | V no los reconoce; Y: `raise_no_formats(expected=True)` | Regla | BR-01 (los incluye) | Propuesto |
| Fallos | Disco lleno por `errno` o `winerror` en toda la cadena | V y B: `is_disk_full_error` (`__cause__`, `__context__`); Y: los cinco caminos del [catálogo, §3.2](failure-conditions.md#32-cómo-llega-la-información-la-cadena-de-causas) | Regla | BR-08, BR-25 | Propuesto; hoy divergente (R-28) |
| Fallos | Reintentos de red propios (2, a 2 y 4 s) | V y B: `yt_download_sync` | Capacidad técnica | BR-07: se delega en yt-dlp | Sustituido |
| Fallos | Cambiar de cliente de YouTube ante 403 o DRM | V: `_YT_PLAYER_CLIENTS` | Exclusión | §6.3 | Excluido |
| Fallos | Regresión con el texto literal reportado | V: pruebas con los dos apóstrofos | Capacidad de validación | SUP-V03 | Propuesto |
| Red | Proxy (configurado o del sistema) | S, K, D: opción `proxy`; V y B: `core/user_env.py`; D, guía §2: recomienda el proxy del sistema y una salida estable, porque rotar la IP rompe sesiones y reanudaciones; Y: `getproxies()` si no se configura | Decisión | D-7; UC-01 A11 | Pendiente (Y ya usa el del sistema) |
| Red | Cookies | S: perfiles por WebView; K: modos con detección por expresión; V y B: `cookies.txt` efímero (0600, ≤1 MB, borrado al terminar); D, guía §3 y §4: cuenta técnica separada, `cookies-from-browser`, misma IP para la sesión y la descarga, cookies tratadas como contraseñas | Decisión | D-1; BR-12 | Pendiente |
| Red | Forzar IPv4, agente de usuario | S | Elemento de configuración (IPv4); exclusión (agente) | UC-20 A7 | Propuesto (revisado en §12) |
| Red | Límite de ancho de banda | S, K, Y: `ratelimit`; D, guía §12: ante la limitación de velocidad del sitio | Requisito suplementario | SUP-P06 | Propuesto |
| Red | Fragmentos concurrentes, aria2c | S, K | Requisito suplementario (fragmentos); tecnología excluida (aria2c) | SUP-P09 | Propuesto (revisado en §12) |
| Red | No descargar en una red medida | S: `CELLULAR_DOWNLOAD`, `isActiveNetworkMetered` | Flujo alternativo | UC-21 A9 | Propuesto (revisado en §12) |
| Red | Ritmo de peticiones | Y: preajuste `-t sleep`; D, guía §8 y §12: pausa entre entradas de una playlist y poca concurrencia | Regla | BR-02 | Propuesto (D-3) |
| Herramientas | ffmpeg con SHA-256 | V: `acquire_bundled`; nosotros: `SOURCE.md` | UC existente | UC-01 A5 | Vigente |
| Herramientas | ffmpeg propio o del sistema | V: `set_custom_path`, `use_system`; K: rutas | UC existente | UC-01 A4, `ffmpeg_path` | Vigente |
| Herramientas | Actualizar yt-dlp desde el programa, y volver a la versión probada | S: canales y periodicidad (`UpdateUtil.kt`); V: capa desde PyPI y «Restore tested version»; K: comprobación diaria | Nuevo UC | UC-27 | Condicionado a D-8 |
| Diagnóstico | Autodiagnóstico ok, aviso o fallo | V: `core/diagnose.py`; B: comprobaciones del asistente de instalación (`api/routers/setup/wizard.py`) | UC existente | UC-01 (`diagnose`), A9 a A11 | Vigente y propuesto |
| Diagnóstico | Paquete de diagnóstico limpio de datos sensibles | V: `core/diagnostic_bundle.py`; S: informe de error | UC nuevo | UC-16, SUP-SEC01, SUP-O03 | Propuesto |
| Diagnóstico | Modo detallado (`-v`) | S | Elemento de configuración | El log ya registra los mensajes de yt-dlp | Vigente |
| Historial | Exportar e importar el historial; modo privado | S | Nuevo UC; flujo alternativo | UC-22; UC-10 A6 | Propuesto (revisado en §12) |
| Windows | Árbol de procesos con Job Object | V: `contained_subprocess.py` | UC existente | SUP-R02, ADR-0013 | Vigente |
| Windows | Vigilancia del proceso padre | V: `parent_liveness.py` | Capacidad técnica | ADR-0013 (`KILL_ON_JOB_CLOSE`) | Vigente |
| Windows | Sin ventanas de consola | V: `CREATE_NO_WINDOW` | Capacidad técnica | Programa de consola; los workers son del mismo proceso | No aplica |
| Windows | yt-dlp sin depender de stdout ni stderr | V: `test_dub_download_stdio.py` | UC existente | `noprogress`, `logger` | Vigente |
| Windows | Archivo bloqueado un instante | V: `fs_retry.py` (~4 s); Y: `wrap_file_access` reintenta `EACCES`, que en Windows reúne los errores 5, 32 y 33 | UC existente | `file_access_retries`; BR-26, UC-17 A6 | Vigente; al agotarse, `UNKNOWN` (R-28) |
| Validación | Separar a quien actúa de quien juzga | V: `tests/probe` («No LLM ever sits on the verdict path») | Capacidad de validación | VBR-04, SUP-V02 | Propuesto |
| Directos | Transmisiones en directo | Y: `is_live`, `wait_for_video` | Excepción | UC-03 E1 | Sin cualificar (D-10) |
| Integridad | Verificar el archivo final | F: `ffprobe`; ninguna referencia lo hace tras descargar | Regla | BR-23, UC-06 A11 | Propuesto (D-9) |
| Integridad | Identificar los archivos de un job buscando la carpeta más reciente | D: `_find_newest_folder`, `_scan_folder` | Regla (evidencia en contra) | BR-17: un job solo reconoce los archivos que reclamó; buscar por fecha puede tomar archivos ajenos | Vigente |
| Integridad | Una cancelación nunca se registra como descarga completada | D: tras `cancel`, `download` devuelve un resultado vacío y el coordinador marca el registro `done` | Regla (evidencia en contra) | UC-05 y el contrato de `JobCompleted` (UC-03 A8): sin archivo final, nunca `COMPLETED` | Vigente |
| Consulta | Salida JSON de `list` y `show` | D: `history list --format json`, `--json` global | Flujo alternativo | UC-08 A5, UC-09 A5 | Propuesto |
| Consulta | Buscar en la cola por título o URL | D: `search_downloads`; S: historial | Flujo alternativo | UC-08 A6 | Propuesto, prioridad baja |
| Integración | Servidor MCP para agentes, lectura de transcripciones y descripciones | D: `infrastructure/mcp/`, 10 herramientas | Requisito suplementario e interfaz diferida; nuevo UC (obtener la información) | SUP-I01, D-17; UC-24 | Propuesto (revisado en §12) |
| Seguridad | Archivo de credenciales creado ya con permisos restringidos | B: `core/user_env.py` (`_opener_0600`) | Requisito suplementario | SUP-SEC03 | Propuesto (condicionado a D-1 y D-7) |
| Archivos | Espacio libre de una carpeta que aún no existe | B: `disk_free_bytes` sube al antecesor existente | Regla | BR-28; UC-01 A10, UC-17 | Propuesto |
| Fallos | Volumen no confiable (`winerror` 448), bloqueo prolongado por sincronización | V y B: `WINDOWS_UNTRUSTED_MOUNT`, `VIDEO_DOWNLOAD_OS_ERROR` | Flujo alternativo | UC-17 A3 y A6; BR-26, BR-27 | Propuesto |
| Validación | Pruebas sin red separadas de las comprobaciones reales, que siguen pendientes hasta ejecutarse | D: `smoke_*.py` frente a «opt-in real validation gates»; marca `e2e` | Capacidad de validación | Clasificación de las pruebas ([plan de E2, §8.2](../project-management/iteration-plan-e2.md#82-clasificación-de-las-pruebas-2026-11-26-main-tras-la-actualización-de-yt-dlp)), VBR-02 | Vigente |

### 6.2 Lo que tenemos y las referencias no

- Una cola persistente que reanuda desde los parciales tras un cierre (S, V y B marcan los trabajos como cancelados o fallidos; D los pierde).
- Playlists y canales con extracción plana y duplicados por media key (V y B no admiten playlists; D descarga una playlist entera como un solo trabajo).
- Propiedad de los nombres finales con reclamaciones (ADR-0030).
- yt-dlp fijado con pruebas de contrato, y deno con yt-dlp-ejs incluidos (V y B usan `ejs:github` sin declarar un runtime de JavaScript; D no declara ninguno).
- El límite de peticiones y el captcha reconocidos como restricción del sitio (propuesto).

### 6.3 Exclusiones

El inventario completo de exclusiones, con su cualificación, está en §12.

## 7. Continuidad, reintentos y recuperación

### 7.1 yt-dlp: línea de comandos, librería y nuestro producto

La línea de comandos de yt-dlp fija valores que la librería no fija. Como el producto usa la librería, hereda los valores de la librería, no los de la línea de comandos.

| Parámetro | Línea de comandos | Librería | Nuestro producto | Efectivo hoy |
|---|---|---|---|---|
| `retries` (HTTP) | 10 (`options.py`) | Sin valor; `RetryManager` lo convierte en 0 | No se pasa | **0** (divergencia, R-24) |
| `fragment_retries` | 10 | Sin valor (0) | No se pasa | **0** (divergencia, R-24) |
| `extractor_retries` | 3 | 3 (`get_param('extractor_retries', 3)`) | No se pasa | 3 |
| `file_access_retries` | 3 | 3 | 10 | 10 |
| `socket_timeout` | 20 s | 20 s (`DEFAULT_TIMEOUT`) | No se pasa | 20 s |
| `retry_sleep_functions` | Sin espera | Sin espera | No se pasa | Sin espera |
| `sleep_interval`, `sleep_interval_requests` | 0; preajuste `-t sleep`: 10 a 20 s y 0,75 s | 0 | No se pasa | 0 |
| `ratelimit` | Sin límite | Sin límite | No se pasa | Sin límite |
| `proxy` | Sin valor: proxy del sistema | Sin valor: `urllib.request.getproxies()` (variables de entorno y registro de Windows) | No se pasa | Proxy del sistema |
| `continuedl` | Activo | Activo | Activo | Activo |
| `updatetime` | Inactivo (`--no-mtime`) | Inactivo | No se pasa | Inactivo |

Las referencias que usan la librería pasan los reintentos de forma explícita: V y B, 10 y 10; D, 5 y 5. Evidencia en la campaña T42: el job 11 falló con `[download] Got error` sin «Giving up after»; con la línea de comandos habría reintentado hasta 10 veces.

### 7.2 Responsabilidades

| Concepto | Responsable | Estado |
|---|---|---|
| Reintento de una petición o un fragmento | yt-dlp (BR-07) | Divergente |
| Reintento del job | Cola, a petición del User (UC-07) | Vigente |
| Espera creciente entre reintentos | yt-dlp dentro del job; la cola entre comprobaciones de una restricción (BR-03) | Pendiente (D-2, D-4) |
| Ritmo de peticiones | yt-dlp dentro de una extracción; la cola entre jobs (BR-02) | Propuesto (D-3) |
| Aplazamiento y control de admisión | Cola (BR-04, BR-09, BR-28; UC-11, UC-17) | Propuesto |
| Pausa, continuación y detención | Cola (UC-14) | Propuesto (D-6) |
| Recuperación tras un cierre | Cola (UC-06, BR-19) | Vigente; A11 propuesto (D-9) |
| Reanudar una descarga desde sus parciales | yt-dlp (`continuedl`) | Vigente |

### 7.3 Política de continuidad ante una condición externa

Ninguna referencia espera un plazo largo: Seal y VoiceStudio fallan el trabajo e informan; Kannagi repite con cookies. Eso indica lo que hacen, no que esperar sea incorrecto. Las alternativas están en D-2.

### 7.4 Acceso: proxy y cookies en una cola persistente

Ninguna decisión está tomada (D-1, D-7). Esta sección separa las necesidades de las soluciones, porque en una cola persistente la configuración de acceso vive más que un comando: se encola hoy y se descarga mañana, en varios workers a la vez y tras un cierre.

**Necesidades distintas que suelen mezclarse:**

| Necesidad | Qué resuelve | Qué no resuelve |
|---|---|---|
| Compatibilidad con la red del sistema | El equipo solo sale por un proxy o una VPN configurados en Windows | Una restricción del sitio |
| Proxy explícito | Una salida distinta de la del sistema, o la del sistema no se detecta | Igual |
| Conexión directa | Ignorar un proxy del sistema que no sirve para el sitio (`proxy: ""` en yt-dlp) | — |
| Acceso autorizado con cuenta | Contenido privado, con restricción de edad o solo para miembros, cuando el User tiene derecho a verlo | No es un medio para saltar una restricción del sitio (BR-12) |
| Diagnóstico de conectividad | Saber si falla la red, el proxy o el TLS interceptado | — |

**Comportamiento de las referencias y de yt-dlp:**

| Fuente | Proxy | Cookies |
|---|---|---|
| yt-dlp 2026.11.23 | `proxy` global de la instancia; sin valor, `urllib.request.getproxies()` (variables de entorno y registro de Windows); `""` fuerza conexión directa; `geo_verification_proxy` aparte | `cookiefile` se lee al crear la instancia y **se reescribe al cerrarla** (`YoutubeDL.save_cookies`); `cookiesfrombrowser` lee la base del navegador en cada instancia. En Windows, Chrome y Edge cifran las cookies con un esquema (`v20`) que `cookies.py` no descifra, y la base no se puede copiar con el navegador abierto (aviso que enlaza el issue #7271); Firefox no tiene esa limitación |
| Seal | Opción global | Perfiles por sitio capturados con WebView |
| Kannagi | Opción global | Modos «cuando haga falta», «preguntar», «siempre», «nunca»; repite con `--cookies-from-browser` al detectar «sign» y «confirm» |
| VoiceStudio, VoiceBlueprintPro | Variables del archivo de entorno del usuario, con diagnóstico de SOCKS sin soporte y de TLS interceptado | `cookies.txt` por importación: formato Netscape, como mucho 1 MB, copia temporal con permisos 0600 borrada al terminar, al fallar o al cancelar |
| YTDownload-2026 | Opción global; su guía recomienda el proxy del sistema y una salida estable | Su guía recomienda una cuenta técnica, `cookies-from-browser` y la misma IP para la sesión y la descarga |

**Dimensiones en una cola persistente:**

| Dimensión | Proxy | Cookies |
|---|---|---|
| Alcance | Global (todas las descargas) o por sitio; por job solo si hay una necesidad real | Por sitio: las cookies de un sitio nunca se envían a otro (yt-dlp ya las filtra por dominio) |
| Configuración por job | Guardar el proxy en las download options lo fijaría a jobs que pueden ejecutarse días después con otra red; se prefiere resolverlo al enviar el job | Igual: el job guarda, como mucho, que necesita acceso con cuenta, nunca las cookies |
| Persistencia | En la configuración (`config.toml` o variable de entorno), no en la base de datos | Archivo del User fuera de la base de datos; nunca copiado a la cola |
| Caducidad | No caduca | Las sesiones caducan y el sitio las rota: un job aplazado puede encontrarlas caducadas al continuar |
| Concurrencia | Sin efecto | yt-dlp reescribe `cookiefile` al cerrar cada instancia: con varios workers, el último en cerrar gana y puede perder cookies renovadas. Necesita una copia por worker o por job, de solo lectura para el original |
| Recuperación | Sin efecto | Tras un cierre, una copia temporal puede quedar en disco: se borra al arrancar (UC-06) |
| Aislamiento | — | Copia temporal por worker en la carpeta del estado, borrada al terminar el job (como VoiceStudio) |
| Información sensible | La URL del proxy puede llevar usuario y contraseña | Las cookies equivalen a una contraseña |
| Exclusión de logs y evidencia | En modo detallado, yt-dlp escribe el mapa de proxies (`Proxy map`, `YoutubeDL.print_debug_header`): el log debe ocultar las credenciales (SUP-SEC01) | Nunca en el log, `diagnose`, el informe (UC-16) ni la evidencia (SUP-SEC01); archivo restringido al usuario (SUP-SEC03) |
| Ciclo de vida | Se lee al enviar cada job | Importar o señalar el archivo; copiar por job; borrar la copia; avisar de caducidad cuando el sitio pide iniciar sesión otra vez |
| Diagnóstico | `diagnose` dice si hay proxy y de dónde viene, sin credenciales (UC-01 A11) | `diagnose` dice si hay cookies configuradas y para qué sitios, nunca su contenido |

**Conclusiones para las decisiones (sin aprobarlas):**
- El proxy del sistema ya funciona sin hacer nada (yt-dlp lo usa); lo que falta es verlo en `diagnose` y ocultar sus credenciales.
- `cookies-from-browser` es poco fiable en el destino del producto (Windows con Chrome o Edge), y el modo «repetir con cookies al ver el error» de Kannagi convierte las cookies en un medio para saltar una restricción, contrario a BR-12.
- Si se adoptan cookies, la forma compatible con una cola persistente es un archivo explícito del User, por sitio, copiado por job y nunca reescrito.

## 8. Estado futuro, prioridad y verificación

### 8.1 Brechas

| Brecha | Estado futuro | Medida de éxito |
|---|---|---|
| Fallos en cadena ante condiciones externas | UC-11 | Ningún job `FAILED` por una condición externa; ningún `retry` manual tras ella |
| Peticiones a un sitio que restringe | BR-02, BR-03 | Ninguna petición al sitio fuera de lo que permite la política |
| 0 reintentos HTTP y de fragmentos | BR-07 | Paridad con la línea de comandos de yt-dlp (SUP-R11) |
| Recuperación que depende del sitio | UC-06 A11 | Un job con evidencia local suficiente se completa sin peticiones |
| Esperas del Evaluador | VUC-04, VUC-08 | Espera por debajo del 10 % de la sesión |
| Pasos de la campaña que dependen de YouTube sin probarlo | VUC-05 | Los pasos 6 a 12 pasan sin red externa |

### 8.2 Prioridad (10.33)

| Prioridad | Elementos |
|---|---|
| **Alta** | UC-11, BR-07 (paridad de reintentos), VUC-04, VUC-05 |
| **Media** | UC-17, UC-06 A11, UC-15, UC-02 A6 y A9, UC-08 A5, UC-09 A5, SUP-R08, SUP-U05, VUC-06 a VUC-08 |
| **Baja** | UC-14, UC-16, UC-23, UC-28, UC-02 A5 y A8, UC-08 A6, UC-10 A5 y A6, UC-20 A7, UC-21 A9, UC-24 A7 y A8 |
| **Media (reconciliación)** | UC-18, UC-20, UC-21, UC-22, UC-24, UC-25, UC-26, UC-02 A7, A10, A11 y A14, UC-15 A5, SUP-I01, SUP-P06, SUP-P09 |
| **Condicionados** | UC-19 (D-1, D-7), UC-27 (D-8), UC-28 (D-14), SUP-M01 (D-18) |
| **Pendiente de cualificación** | UC-02 A7, el candidato «Actualizar yt-dlp» (D-8) |

### 8.3 Verificación de los requisitos (7.2)

| Característica | Cómo se cumple |
|---|---|
| Atómicos | Un caso de uso por objetivo; una directiva por regla; un valor por parámetro |
| Completos | Todos los casos de uso tienen los campos comunes ([modelo, §2](use-case-model.md)); la matriz del §5 del modelo cuenta los flujos |
| Consistentes | Una sola autoridad por concepto: reglas en el catálogo, condiciones en su catálogo, términos en el vocabulario |
| Factibles | Cada regla se apoya en una capacidad comprobada de yt-dlp 2026.11.23 o de la biblioteca estándar |
| Comprobables | Cada caso de uso tiene criterios de aceptación y escenarios de prueba; cada requisito suplementario, un criterio |
| Priorizados | §8.2 |

## 9. Decisiones

**Disposición del Responsable (2026-11-26, instrucción 2.2.0):**
- se aceptan los 26 casos de uso;
- se aprueban las resoluciones funcionales de D-1 a D-20.

Cada decisión separa la resolución funcional (qué debe hacer el producto, ya aprobado) de la cualificación técnica (cómo, con qué evidencia).

**Estados técnicos:**
- **Cualificada:** evidencia suficiente para la solución.
- **Recomendada con evidencia:** hay una alternativa preferida y la evidencia que la apoya, con alguna limitación.
- **Condicionada:** depende de otra decisión o de una condición externa.
- **Pendiente de medición.**
- **Pendiente de Windows:** solo se demuestra en la plataforma objetivo.
- **Pendiente por evidencia insuficiente.**
- **Pendiente de decisión excepcional del Responsable.**

**Fuentes de la evidencia:**
- los experimentos de cualificación ([resultados](../notes/experiments/requirements-qualification.md));
- la inspección del código de yt-dlp 2026.11.23 y del producto en `7dc9842`;
- las referencias del §5.1.

La relación entre decisiones está en el §13.10.

### 9.1 Resolución

| Decisión | Resolución funcional (aprobada) | Alternativa técnica recomendada | Evidencia | Estado técnico | UC afectados | Condición pendiente |
|---|---|---|---|---|---|---|
| D-15 Resultados | Cero, uno o N resultados por job; lo pedido es obligatorio salvo que se marque opcional; completar exige todos los obligatorios | Job con N resultados registrados (tipo, obligatoriedad, estado, ruta, reclamación y evidencia de publicación); `output_path` se conserva como resultado principal por compatibilidad | Inspección de `Job`, `JobCompleted`, `output_claims` y de la migración 0003 (§13.1) | Recomendada con evidencia | 03, 05, 06, 07, 09, 10, 24, 25, 26 | Diseño del esquema en Analysis and Design |
| D-16 Identidad | Separar la identidad del contenido de la del resultado pedido; las variantes son legítimas | Identidad de la petición = media key + especificación normalizada del resultado, con versión del algoritmo de identidad; «ya descargado» como `SKIPPED` informativo | Inspección de `has_active_download` y de la migración 0002 (§13.2) | Recomendada con evidencia | 02, 03, 18, 22, 23, 24 | La equivalencia de selectores solo es sintáctica |
| D-18 Transformaciones | Las transformaciones ligadas a la obtención, sin editor general | Postprocessors de yt-dlp y ffmpeg incluido (§13.3, §13.4) | Inspección de yt-dlp; configuración de la build | Recomendada con evidencia; recodificar a H.264 o HEVC, **pendiente de decisión excepcional** (R-29) | 02, 03, 15 | `ffmpeg -encoders` en Windows; patentes |
| D-19 Perfiles | Las preferencias que determinan el resultado se fijan al encolar | Copiar en el job las opciones de resultado; referenciar el acceso por nombre y resolverlo al enviar | Las download options ya se fijan al encolar (UC-02; pruebas de `enqueue`) | **Cualificada** | 02, 18, 19, 20 | — |
| D-9 Recuperación | Recuperación local primero | Evidencia por resultado: registro, reclamación con owner token, publicación y comprobación estructural con ffprobe frente a lo esperado registrado antes de publicar | ADR-0030; recorrido de las fronteras de interrupción (§13.11) | Recomendada con evidencia | 06, 07, 23, 26 | Registrar la expectativa (duración, streams) antes de publicar |
| D-11 Purga y archivos | Registros y archivos separados; borrar es explícito y autorizado | Nivel de evidencia por operación (§13.12); registrar tamaño, fecha y, opcionalmente, hash al publicar | ADR-0030; YTDownload-2026 como antiejemplo | Recomendada con evidencia | 10, 25 | Coste del hash: pendiente de medición |
| D-5 Almacenamiento preventivo | Comprobación adaptativa, sin un límite fijo | Estimar con `filesize` o `filesize_approx`, más el espacio reservado por los jobs activos de la unidad y la medición sobre el antecesor existente | yt-dlp suma `filesize_approx` de los formatos unidos y la estima por `tbr` × duración (`YoutubeDL.py`) | **Pendiente de medición** (factor de unión, margen) y **de Windows** (cuotas en `shutil.disk_usage`) | 01, 17 | SUP-P07 |
| D-12 Fallos de almacenamiento | Clasificar por causa, alcance, temporalidad y recuperabilidad | Ampliar el clasificador existente con el recorrido de la cadena (BR-25), y usar el texto solo como último recurso | Experimento `cause_chain`: 3 de 5 caminos recuperan el `errno`; 2 solo tienen texto | Recomendada con evidencia; traducción de `winerror` **pendiente de Windows** | 03, 11, 17 | Prueba `windows` de los códigos |
| D-1 Cookies | Archivo de cookies del User, perfiles, selección por job y por sitio, validación, renovación y caducidad | `cookiefile` de yt-dlp con una copia por job (yt-dlp reescribe el archivo al cerrar) en la carpeta de estado, restringida al usuario y limpiada al arrancar | `YoutubeDL.save_cookies`; VoiceStudio | Recomendada con evidencia; ACL en Windows **pendiente de Windows**; cookies del navegador **condicionada** | 02, 19 | Cifrado `v20` de Chrome y Edge |
| D-7 Proxy | Modos sistema, directo y explícito | Sistema: sin `proxy`; directo: `proxy=""`; explícito: `proxy=URL`. Enmascarar las credenciales en el origen (logger y mensajes) | `YoutubeDL.proxies` (`__noproxy__`, `getproxies()`) | **Cualificada** (modos); enmascarado recomendado | 01, 19, 20, 16 | SOCKS con el gestor `requests`: sin comprobar |
| D-2 Continuidad | Continuidad selectiva y política configurable cuando nada es elegible | Admisión en `run` por alcance (job, sitio, recurso, sistema); el aplazamiento deja el job `PENDING` con su condición; ningún estado nuevo; política `wait(límite)` o `stop` | `run_queue`, `get_next_pending`, `--keep-waiting` | Recomendada con evidencia; límites **pendientes de medición** | 03, 04, 11, 14, 17, 21 | Valores de espera |
| D-3 Ritmo | Capacidades nativas de yt-dlp; sin un intervalo universal | Reintentos con los valores de la línea de comandos (corrige R-24); ritmo por sitio en la admisión de `run`; `sleep_interval_requests` dentro de la extracción | Experimento `retries`: 0 reintentos → `FAILED` a la primera; 10 → completa | **Cualificada** (R-24); valores de ritmo **pendientes de medición** | 03, 11, 15 | Ritmo por sitio |
| D-4 Restricciones temporales | Política limitada, configurable y según la condición | Respetar `Retry-After`, leído del `HTTPError` en la cadena (yt-dlp no lo usa); un 403 no se considera temporal por defecto | No hay ninguna referencia a `Retry-After` en yt-dlp; `HTTPError.response` | Recomendada con evidencia; valores **pendientes de medición** | 03, 11 | Plazos |
| D-6 Pausa | Pausa gradual e inmediata recuperable; reanudar, cancelar, detener y reintentar distintos | Job requests de cola en la bandeja existente; pausa inmediata con la interrupción existente (UC-05 A6); la intención de pausa persiste en SQLite | Bandeja de job requests; árbol de procesos (ADR-0029) | Recomendada con evidencia | 05, 14, 21 | Pausa en una base de datos restaurada (§13.13) |
| D-13 Programación | Capacidad propia: inicio único, recurrencia, ventanas, recuperación tras reiniciar y ejecuciones omitidas | Programación guardada en el estado; `run` evalúa las ventanas (admisión); para arrancar sin `run` activo, una tarea propia del Programador de tareas (`schtasks.exe`, incluido en Windows); sin servicio residente | `run --keep-waiting`; Windows | Recomendada con evidencia; **pendiente de Windows** | 21 | Suspensión e hibernación |
| D-20 Ancho de banda | Límite individual y global configurable | Global repartido por `run` al enviar cada job; límite por job dividido entre los fragmentos concurrentes | `ratelimit` se lee en cada bloque y por transferencia; los descargadores de fragmentos reciben una copia de los parámetros (`fragment.py`) | Recomendada con evidencia (inspección); agregado real **pendiente de medición** | 03, 21 | Medir N fragmentos frente al límite |
| D-8 Dependencias | Administración controlada, verificable y reversible | Consultar y diagnosticar (UC-01); adoptar versiones cualificadas del repositorio (`uv.lock`); candidata en un entorno aislado; ningún cambio con jobs activos | ADR-0002, SUP-S01, procedimiento de actualización | Recomendada; candidata **condicionada** | 01, 27 | Procedencia de las candidatas |
| D-10 Directos | Directos y programados dentro del alcance | Programado (`live_status == "is_upcoming"`, `release_timestamp`): la cola lo aplaza hasta su hora, sin `wait_for_video` en un worker. Activo: yt-dlp, con duración máxima configurable | `YoutubeDL.py` (`wait_for_video` espera dentro del proceso) | Recomendada con evidencia; recursos **pendientes de medición** | 03, 11, 14, 17, 21 | Reanudación de directos |
| D-14 Avisos | Avisos configurables de los sucesos operativos | Registro de sucesos JSON (biblioteca estándar) y resumen; la notificación de Windows necesita una dependencia o PowerShell | La biblioteca estándar no tiene API de notificaciones | Registro **cualificado**; notificación de Windows **pendiente por evidencia insuficiente** | 20, 28 | Dependencia para las notificaciones |
| D-17 Integración | Requisito transversal; CLI primero; lógica reutilizable sin `argparse` | Contrato JSON versionado y errores estructurados; API Python = los módulos de caso de uso de ADR-0017 cuando sean estables; modelo de confianza por interfaz (§13.7) | ADR-0001, ADR-0017; `job_queue/*` ya separados de `command_line` | Recomendada con evidencia | Todos | Esquemas del contrato |
| D-21 Retención y privacidad (nueva) | Necesidad aprobada en la instrucción 2.2.0, §32 | Retención por clase de dato (§13.14): purga del historial configurable, rotación de logs vigente, exportaciones y respaldos sin secretos | `log_file.py`, UC-10, BR-34 | Recomendada; valores **pendientes de decisión excepcional** (plazos por defecto) | 10, 20, 22, 23 | Plazos de retención |

**Conteo:**
- **Resoluciones funcionales:** 21 resueltas, 20 de ellas aprobadas por el Responsable; D-21 tiene una necesidad aprobada y sus valores, pendientes.
- **Estado técnico:**
  - cualificadas por completo: 2 (D-7 en los modos, D-19); cualificadas en parte: D-3 (R-24) y D-14 (registro);
  - con alternativa recomendada: las 21;
  - dependen de mediciones: 8 (D-2, D-3, D-4, D-5, D-10, D-11, D-20, D-21);
  - dependen de Windows: 5 (D-1, D-5, D-12, D-13, D-18);
  - necesitan evidencia adicional: 2 (D-14, D-7 con SOCKS);
  - contradicciones: 1, resuelta (§13.16);
  - requieren una decisión excepcional del Responsable: 2 (R-29 en D-18, plazos en D-21).

### 9.2 Detalle por decisión

Para cada decisión: necesidad · resolución · flujos · reglas · requisitos · riesgos · alternativas · mecanismos existentes · evidencia · impacto · compatibilidad · criterios de aceptación · limitaciones.

**D-15. Resultados de un job.**
- **Necesidad:** representar N resultados con obligatoriedad (§13.1).
- **Flujos:** UC-03 A16 y A17, UC-05 A9, UC-06 A11 y A12, UC-07 A8, UC-09 A6, UC-24, UC-25 y UC-26.
- **Reglas y requisitos:** BR-29 a BR-31, BR-38; SUP-P08.
- **Riesgos:** R-30.
- **Alternativas:**
  - (a) jobs hijos por resultado: descartada, porque multiplica los jobs de una sola petición y complica la cancelación y la purga;
  - (b) N resultados por job: recomendada;
  - (c) principal más manifiesto: descartada, porque deja los complementarios sin reclamación.
- **Mecanismos existentes:** reclamaciones (ADR-0030), owner token, `FinalPathRecorder`, carpeta de parciales.
- **Impacto:**
  - `Job` y `JobCompleted` llevan una colección de resultados;
  - una migración nueva y progresiva añade el registro de resultados y conserva `output_path` como principal;
  - la reclamación pasa a hacerse por resultado;
  - las consultas, la purga, el respaldo y la verificación leen el registro.
- **Compatibilidad:** un job anterior tiene un resultado principal, migrado desde `output_path`; las migraciones publicadas no se tocan.
- **Criterios de aceptación:** BR-30; UC-03 A16 y A17; R-30 cerrado cuando todo archivo escrito tenga reclamación.
- **Limitación:** no se eligen tablas ni eventos en esta etapa.

**D-16. Identidad.**
- **Necesidad:** §13.2.
- **Reglas:** BR-13, que queda divergente respecto de la resolución, y BR-32.
- **Flujos:** UC-03 A1 (divergente), UC-22 A3, UC-24 A5.
- **Alternativas:**
  - (a) mantener BR-13: descartada por la resolución;
  - (b) identidad por especificación: recomendada;
  - (c) identidad por perfil: descartada, porque el nombre de un perfil no es una identidad (D-19).
- **Mecanismos existentes:** `MediaKey`, el índice `unique_active_download_per_media` (migraciones 0001 a 0003) y `canonical_stem_path`, que ya normaliza rutas como NTFS.
- **Impacto:** una migración nueva sustituye el índice por uno sobre la identidad de la petición. Los datos existentes reciben una identidad calculada de sus download options con la versión 1 del algoritmo.
- **Criterios:**
  - dos peticiones que solo difieren en opciones operativas (timeout, workers, reintentos, registro, progreso) son duplicadas;
  - dos que difieren en calidad, contenedor, transformación, complementarios o destino son variantes;
  - lo ya descargado se informa como `SKIPPED` con su ruta, nunca como `FAILED`.
- **Limitación:** no se decide la equivalencia semántica entre dos selectores distintos sin conocer los formatos.

**D-18. Transformaciones.**
- **Necesidad:** resultados compatibles y transformados (§13.3, §13.4).
- **Flujos:** UC-02 A7, A8, A10, A11 y A14; UC-03 A17 a A19; UC-15 A6.
- **Requisitos y riesgos:** SUP-M01; R-29.
- **Alternativas:** postprocessors de yt-dlp (recomendada) frente a llamadas propias a ffmpeg (descartada: duplica responsabilidades).
- **Mecanismos de yt-dlp:**
  - `FFmpegVideoRemuxer`, `FFmpegVideoConvertor`, `FFmpegExtractAudio`;
  - `FFmpegSubtitlesConvertor`, `FFmpegEmbedSubtitle`, `FFmpegMetadata`, `EmbedThumbnail`;
  - `SponsorBlock` con `ModifyChapters`, `FFmpegSplitChapters`;
  - `download_ranges` con `force_keyframes_at_cuts`.
- **Evidencia:** §13.4. Los cortes exactos recodifican (`force_keyframes` usa `stream_copy_opts(False)`).
- **Contradicción resuelta:** eliminar segmentos es un resultado pedido; si SponsorBlock no responde, el multimedia se conserva y el postprocesamiento se repite (UC-03 A18).
- **Criterios:**
  - cada transformación produce el contenedor, los códecs o los segmentos pedidos según ffprobe;
  - el original se conserva cuando se pide.
- **Limitaciones:**
  - la lista efectiva de codificadores se confirma con `ffmpeg -encoders` en Windows;
  - recodificar a H.264 o HEVC con `libopenh264` o `libkvazaar` requiere la decisión del Responsable sobre patentes (R-29); VP9 y AV1 no tienen esa condición.

**D-19. Perfiles.**
- **Necesidad:** §13.5.
- **Evidencia:** las download options ya se copian en el job al encolar (UC-02, postcondición; pruebas de `enqueue`), así que el contrato está demostrado.
- **Separación:**
  - **resultado y postprocesamiento:** fijados en el job;
  - **operativo y recursos** (workers, límites, reintentos, ritmo): se resuelven al ejecutar y no forman parte de la identidad;
  - **acceso:** referencia por nombre, resuelta al enviar.
- **Borrar un perfil referenciado:** los jobs conservan su copia y el nombre y la versión del perfil como traza (BR-33); su recuperación no depende del perfil.
- **Criterios:** UC-18, criterio 1.

**D-9. Recuperación local.**
- **Necesidad:** R-25.
- **Flujos:** UC-06 A4 (defecto), A11 y A12; UC-07 A8; UC-23 A2; UC-26.
- **Regla:** BR-23.
- **Evidencia:** fronteras de interrupción (§13.11). La carpeta de parciales está dentro de la carpeta de descargas, así que la publicación es un renombrado en la misma unidad, atómico en NTFS y en POSIX.
- **Alternativas:**
  - (a) volver a extraer (hoy): defectuosa;
  - (b) evidencia local: recomendada;
  - (c) volver a descargar siempre: descartada.
- **Criterios de regresión de R-25:** con el sitio inaccesible (servidor local detenido), un job interrumpido tras publicar todos sus resultados termina `COMPLETED` sin peticiones; uno con un resultado truncado no.
- **Limitación:** comprobar la integridad completa con decodificación es costoso; el nivel lo fija BR-38.

**D-11. Purga y archivos.**
- **Necesidad:** §13.12.
- **Alternativas:** mismo nivel de evidencia para todas las operaciones (descartada) frente a un nivel por operación (recomendada).
- **Criterios:** UC-25, criterios 1 a 3.
- **Limitación:** sin hash, un archivo sustituido con el mismo tamaño y fecha no se detecta. El hash es opcional y su coste se mide.

**D-5. Almacenamiento preventivo.**
- **Necesidad:** §16 de la instrucción.
- **Mecanismos existentes:**
  - `shutil.disk_usage` sobre el antecesor existente (VoiceBlueprintPro);
  - `filesize` y `filesize_approx` de yt-dlp, que suma los de los formatos unidos y estima por `tbr` × duración.
- **Alternativa recomendada:** estimación por job, más el espacio comprometido por los jobs activos de la misma unidad, más un margen. Se reevalúa en cada envío y la reacción siempre está activa (UC-17).
- **Limitaciones:**
  - el factor de unión, el margen y la memoria quedan pendientes de medición (SUP-P07);
  - si `shutil.disk_usage` refleja la cuota del usuario en Windows queda pendiente de Windows.

**D-12. Fallos de almacenamiento.**
- **Evidencia:** experimento `cause_chain`.
- **Alternativa recomendada:** un solo clasificador, el existente, ampliado:
  - prioridad: código estructurado en la cadena (`winerror`, después `errno`), luego el tipo de excepción, luego el texto;
  - con protección contra ciclos.
- **Criterios de regresión de R-28:** los cinco caminos del catálogo, §3.2, terminan con la condición de almacenamiento correcta; los tres con `errno` la identifican sin texto.
- **Limitación:** las traducciones de `winerror` se confirman en Windows.

**D-1. Cookies.**
- **Necesidad:** §18 de la instrucción.
- **Flujos:** UC-19, UC-02 A12.
- **Requisitos:** SUP-SEC01, SUP-SEC03 y SUP-SEC04.
- **Riesgos:** R-27.
- **Alternativas:**
  - (a) `cookiefile` con una copia por job: recomendada;
  - (b) el original pasado directamente: descartada, porque yt-dlp lo reescribe;
  - (c) `cookiesfrombrowser`: condicionada (`v20` en Chrome y Edge; base de datos bloqueada con el navegador abierto).
- **Protección:**
  - en POSIX, crear con `os.open` y modo 0600;
  - en Windows el modo no tiene efecto: la copia hereda la ACL de la carpeta de estado bajo el perfil del usuario, que se verifica (pendiente de Windows);
  - sin cifrado propio.
- **Renovación autorizada:** el User reemplaza el archivo (UC-19 A4). Nunca se escribe el original.
- **Criterios:** UC-19, criterios 1 a 4.

**D-7. Proxy.**
- **Modos:** como en la tabla.
- **Precedencia:** argumento por job, perfil de acceso, configuración, sistema.
- **Enmascarado en el origen:** `YtDlpLogger` y los mensajes de error ocultan `usuario:contraseña@` antes de llegar al log, a la base de datos (`failure_message`), al JSON y al informe (SUP-SEC01).
- **Credenciales inválidas:** `ProxyError`, clasificado `NETWORK`, con la indicación de revisar el proxy (catálogo, §2).
- **Limitación:** el soporte de SOCKS en el gestor `requests` no está comprobado.

**D-2. Continuidad.**
- **Evidencia:** la planificación ya está en el proceso de `run`. `--keep-waiting` ya espera jobs nuevos.
- **Alternativa recomendada:**
  - la admisión filtra los jobs afectados por una condición conocida;
  - el aplazamiento se expresa con datos del job (condición y alcance), no con un estado nuevo;
  - si nada es elegible, se aplica la política `when_blocked` (esperar con un límite o terminar de forma ordenada; valores pendientes).
- **Intentos:** solo `retry` del User incrementa `attempt_count` (BR-15). Ni los reintentos internos de yt-dlp, ni un aplazamiento, ni una admisión denegada lo hacen.
- **Estados operativos de la cola que no son equivalentes** (resumen de `run` y `list`):
  - vacía;
  - con jobs terminados;
  - en pausa;
  - con jobs programados;
  - con jobs impedidos;
  - con jobs que requieren intervención.
- **Criterios:** UC-11, criterios 1 a 5.

**D-3. Ritmo y R-24.**
- **Alcance de cada parámetro** (inspección):

  | Parámetro | Alcance |
  |---|---|
  | `sleep_interval`, `max_sleep_interval` | Antes de cada descarga de la instancia |
  | `sleep_interval_requests` | Entre peticiones de una extracción |
  | `ratelimit` | Por transferencia |
  | `concurrent_fragment_downloads` | Hilos por descarga |
  | `retries`, `fragment_retries`, `extractor_retries`, `file_access_retries` | Reintentos por tipo de operación |
  | `retry_sleep_functions` | Espera entre reintentos |
  | `socket_timeout` | Por conexión |

- **Regulación global:** ningún parámetro es global entre workers, así que el ritmo por sitio vive en la admisión de `run`.
- **Criterios de regresión de R-24:**
  - el experimento `retries`, convertido en prueba de contrato: con dos 503 seguidos, el job se completa;
  - con más fallos que reintentos, falla `NETWORK` con «Giving up after».

**D-4. Restricciones temporales.**
- **Clasificación:** §22.2 de la instrucción, incorporada al catálogo de condiciones, §2.
- **Evidencia:** yt-dlp no lee `Retry-After`; el `HTTPError` de la cadena conserva la respuesta y sus cabeceras.
- **Alternativa recomendada:** respetar `Retry-After` cuando exista y, si no, un plazo creciente con un límite.
- **Limitación:** los valores no tienen evidencia; se medirán con la restricción real cuando ocurra (sin provocarla).

**D-6. Pausa.**
- **Reutilización:** bandeja de job requests (`PAUSE`, `RESUME`, `STOP`), interrupción y terminación del árbol de procesos (ADR-0013, ADR-0029).
- **Persistencia:**
  - la intención de pausa sobrevive a un cierre normal, un reinicio, una interrupción y el apagado;
  - tras restaurar un respaldo (UC-23), `run` arranca informando del estado de pausa restaurado y no lo cambia por su cuenta.
- **Diferencias:**
  - la pausa conserva la intención y los jobs;
  - la cancelación expresa que ya no se quiere el job;
  - terminar el proceso (`Ctrl+C`) es una interrupción sin intención persistida.

**D-13. Programación.**
- **Semántica:**
  - hora local con zona;
  - las ventanas pueden cruzar la medianoche;
  - horario de verano según la hora local;
  - con el equipo apagado o suspendido, una ventana abierta al arrancar se aprovecha y un inicio único omitido se informa y se ejecuta según `missed_start_policy` (pendiente);
  - no se ejecuta dos veces la misma programación (identificador y última ejecución persistidos).
- **Sin servicio residente.** La tarea del Programador de tareas solo arranca `run`.

**D-20. Ancho de banda.**
- **Alcance garantizable:**
  - por job: `ratelimit` dividido entre los fragmentos concurrentes;
  - global: el reparto al enviar cada job.
- **Limitaciones:**
  - un cambio durante una descarga activa solo afectaría a transferencias no fragmentadas y requiere comunicarlo al worker: se aplica al siguiente job;
  - el postprocesamiento no consume red.

**D-8. Dependencias.**
- **Responsabilidades:**
  - **User:** consultar versiones y adoptar las cualificadas;
  - **Mantenedor:** cualificar con las pruebas de contrato (SUP-S01);
  - **producto:** diagnosticar e impedir cambios con jobs activos;
  - **procedimiento de desarrollo:** el de `yt-dlp-update-procedure.md`.
- ADR-0002 sigue vigente; UC-27 no lo sustituye.

**D-10. Directos.**
- **Necesidades de recursos:** un programado no ocupa un worker; un activo tiene una duración máxima configurable y su espacio se reserva con D-5.
- **Reanudación:** distinta de un archivo. Tras una interrupción, el directo continúa desde el momento actual (los fragmentos perdidos se informan) salvo con `live_from_start`, que depende del sitio.
- **Criterios:** UC-03 E1, reescrito por esta resolución.

**D-14. Avisos.**
- **Preferencias:** en UC-20.
- **Garantías:**
  - un fallo al avisar no cambia la cola (UC-28 E1);
  - el registro de sucesos no contiene secretos.

**D-17. Integración.**
- **Operaciones del §29.2:** todas tienen un caso de uso; el canal no crea casos de uso nuevos.
- **Contrato:** JSON versionado por comando, códigos de error estables, sucesos (D-14) y sin secretos.
- **Modelo de confianza:** §13.7.

**D-21. Retención y privacidad.**
- **Necesidad:** §32 de la instrucción. Se representa con UC-10 A6, UC-20, UC-22, UC-23, SUP-D01 y BR-34, sin un caso de uso nuevo.
- **Alternativas:** retención indefinida (hoy), plazos configurables por clase, o modo sin historial.
- **Recomendación:** plazos configurables por clase, con los valores por defecto que decida el Responsable.

## 10. Limitaciones del análisis

- Kannagi no tiene versión ni historial: sus hallazgos no se pueden fechar.
- YTDownload-2026 no declara licencia: solo aporta ideas, y su guía está en ruso (se tradujo para el análisis).
- La configuración de la build de ffmpeg se leyó del binario (`avcodec-63.dll`), sin ejecutar `ffmpeg.exe` en Windows: la lista efectiva de codificadores se confirma en la campaña.
- No se ejecutaron SponsorBlock, la división por capítulos ni las secciones contra un sitio real; las capacidades se leyeron en el código de yt-dlp 2026.11.23.
- VoiceBlueprintPro se analizó por diferencias con VoiceStudio; los archivos idénticos o solo renombrados no aportan hallazgos propios.
- El checkout de FFmpeg es parcial: los contratos se comprobaron con los binarios incluidos, no con su código.
- Ningún hallazgo de comportamiento se ejecutó contra un sitio real: la campaña está en pausa por la restricción de YouTube.
- Los parámetros pendientes (§3 del catálogo de reglas) no tienen evidencia; no se proponen valores.
- Las condiciones de Windows (suspensión, disco lleno real, rutas largas) solo se verifican en la campaña. La traducción de `winerror` 39, 1295, 21 y 53 a `errno` está por confirmar con una prueba `windows`.
- Los caminos de error del §3.2 del catálogo se reprodujeron provocando cada error en el punto del código de yt-dlp; no con un disco lleno real.

## 11. Trabajo propuesto

La cobertura de las tareas candidatas respecto de los 26 casos de uso aceptados está en el §14.2.

Las tareas T52 a T67 son **candidatas**, no un plan. La reconciliación del §12 añadió capacidades que afectan transversalmente a la identidad (D-16), a los resultados (D-15), a la configuración (D-19) y a las interfaces (D-17). La descomposición definitiva y su secuencia se harán después de resolver esas decisiones, en el plan de E3. No se crean tareas nuevas para UC-18 a UC-28.

Ninguna tarea empieza hasta que el Responsable apruebe las decisiones de las que depende.

| Tarea | Contenido | Prioridad | Depende de |
|---|---|---|---|
| T52 | Aplazar un job (`JobDeferred`), reconocer las condiciones externas (BR-01, BR-05) con pruebas de contrato | Alta | D-1, D-2 |
| T53 | Política de continuidad y control de admisión por sitio, conectividad y unidad (UC-11) | Alta | T52, D-2 a D-5 |
| T54 | Paridad de reintentos con la línea de comandos de yt-dlp (BR-07, SUP-R11) | Alta | — |
| T55 | Completar con evidencia local (UC-06 A11) | Media | D-9 |
| T56 | `list`, `show` y `diagnose` con los aplazamientos, el destino y el proxy (UC-08 A4, UC-09 A4, UC-01 A9 a A11) | Media | T53, D-7 |
| T57 | Evitar la suspensión del equipo con jobs en curso (SUP-R08) | Media | — |
| T58 | Pausa, continuación y detención (UC-14); límite de ancho de banda (SUP-P06) | Baja | D-6 |
| T59 | Medios locales para la validación (VUC-05) | Alta | — |
| T60 | Bloques de la campaña con comprobación automática y resumen (VUC-04, VUC-08) | Alta | T59 |
| T61 | Comprobación del acceso al sitio y paquete de evidencia (VUC-06, VUC-07), compartido con UC-16 | Media | — |
| T62 | Consultar un contenido (UC-15) y seleccionar entradas (UC-02 A6, UC-04 A8) | Media | — |
| T63 | Indicación de si reintentar sirve (SUP-U05) | Media | — |
| T64 | Informe de diagnóstico (UC-16) con limpieza de datos sensibles (SUP-SEC01) | Baja | T61 |
| T65 | Directos (UC-03 E1) y purgar con archivos (UC-10 A5) | Baja | D-10, D-11 |
| T67 | Condiciones de almacenamiento: identificación en toda la cadena de causas (BR-25, corrige R-28), comprobación preventiva (BR-28) y tratamiento por condición (UC-17) | Media; la identificación, alta | T52, D-5, D-12 |
| T66 | Preajustes de calidad (UC-02 A9), salida JSON y búsqueda (UC-08 A5 y A6, UC-09 A5) | Media | — |

## 12. Reconciliación de exclusiones

Revisión del 2026-11-26 (instrucción 2.1.0). **Situación posterior:** el Responsable aceptó el alcance de los 26 casos de uso y las resoluciones funcionales de D-1 a D-20 (instrucción 2.2.0). Donde esta sección dice «condicionado», hoy significa condición técnica de un escenario, no una exclusión del objetivo (§9). Se localizaron las exclusiones de todos los artefactos:
- la visión (§6);
- el modelo de casos de uso (§4.2);
- este análisis (§4.1, §6.1 y §6.3);
- los ADR, los planes de iteración y las especificaciones.

Cada una se cualificó separando la **necesidad** del User de la **solución** que se había excluido.

**Criterios válidos de exclusión:**
- fuera del dominio;
- sin objetivo funcional;
- duplicada;
- contraria a una restricción vigente;
- licencia incompatible;
- solo una tecnología innecesaria;
- interfaz diferida;
- evidencia de que no se necesita.

**Criterios que no son motivo:** que no esté implementado, que sea difícil, que afecte a varios componentes, que otra herramienta lo haga o que tenga prioridad baja.

**Columnas de la tabla:**
- **Origen:** S, V, B, D, K, Y y F, como en §6.
- **Clasificación:**
  - **M:** se mantiene excluida;
  - **T:** solo una tecnología; la necesidad tiene otro destino;
  - **I:** interfaz diferida;
  - **P:** decisión de soporte o distribución;
  - **A:** amplía un caso de uso existente;
  - **N:** nuevo caso de uso;
  - **R:** requisito suplementario;
  - **L:** localizada, pero no es una exclusión de alcance.

### 12.1 Inventario

| # | Exclusión (dónde) | Necesidad · actor · resultado esperado | Origen | Hoy | Justificación original | ¿Válida? | ¿Necesidad o solución? | Clasificación y destino | Impacto de incorporarla · consecuencia de excluirla |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Interfaz gráfica (visión, ADR-0001, §6.3) | Interactuar sin la línea de comandos · User · ver y operar la cola | S, D, K | Solo CLI | Alcance inicial | Sí, para la implementación | Solución (canal) | **I**: diferida; sus necesidades ya están en los casos de uso; SUP-I01 | Un canal más sobre los mismos servicios · ninguna necesidad queda sin cubrir |
| 2 | Temas visuales (§6.3) | Personalizar el aspecto · User | D, S, K | — | Alcance inicial | Sí | Solución | **M**: sin necesidad en una CLI | — |
| 3 | Otras plataformas, Windows ARM64 (visión, ADR-0004) | Usar el producto en otro sistema · User | — | Solo Windows x64 | Plataforma objetivo | Sí, como decisión de soporte | Decisión de soporte | **P**: SUP-C06 | Ampliar la matriz de pruebas · sin soporte, pero el núcleo es portable |
| 4 | Publicación en PyPI (visión) | Instalar con `pip` · User | — | Clon con `uv sync` | — | Sí, mientras el procedimiento actual baste | Alternativa de distribución | **P**: SUP-C07 | Empaquetar ffmpeg y deno aparte · ninguna |
| 5 | Recodificar video (visión: «la build LGPL no incluye H.264/H.265») | Resultado reproducible en los dispositivos del User · User | S, K, Y, F | Solo unión, sin recodificar | Falta de codificadores | **No**: la build incluida trae `libopenh264` (H.264), `libkvazaar` (HEVC), VP8, VP9, AV1 y codificadores por hardware (§13.4) | Necesidad | **A**: UC-02 A14, UC-03 A19; **R**: SUP-M01; decisión D-18; R-29 | Recodificar es lento y caro en CPU · el User recodifica a mano fuera del producto |
| 6 | PO Tokens (visión, §6.3, BR-12) | — | Wiki de yt-dlp | — | Decisión del Responsable | Sí (aprobada) | Mecanismo | **M**: restricción vigente | — |
| 7 | Evadir controles del sitio (visión) | — | — | — | Restricción legítima | Sí | Mecanismo | **M** | — |
| 8 | Cambiar de cliente de YouTube ante un 403 (§6.1, §6.3) | Descargar pese a un 403 · User | V, B | El job falla `NETWORK` | Exige PO Token; contrario a BR-12 | Sí | Mecanismo | **M**; la necesidad (no perder el job) es UC-11 | — |
| 9 | Servidor MCP y herramientas para agentes (visión, §6.1, §6.3) | Que otros programas usen el producto sin interpretar texto · Programa cliente | D | Sin salida estructurada | «La salida JSON cubre la automatización» | **No**: JSON en dos comandos no cubre encolar, cancelar ni errores estructurados | Necesidad (integración) y solución (MCP) | **R**: SUP-I01; **I**: MCP o API, diferidos (D-17) | Contrato estable en todos los comandos · los programas dependen de texto frágil |
| 10 | Leer transcripciones y descripciones (§6.3) | Obtener la información que publica el sitio · User | D, Y | No se descarga | «El producto no interpreta archivos» | Solo para interpretar | Necesidad (obtener) frente a solución excluida (interpretar o generar con IA) | **N**: UC-24; **A**: UC-02 A7, UC-03 A16 | Resultados no multimedia (D-15) · el User usa yt-dlp aparte |
| 11 | Navegador automatizado para iniciar sesión (§6.3) | Acceso con cuenta · User | D | Sin acceso con cuenta | Dependencia grande | Sí, como tecnología | Tecnología | **T**: la necesidad es UC-19 | — |
| 12 | SponsorBlock (visión, §6.1, §6.3) | Contenido sin patrocinios o con ellos marcados · User | S, Y | No | «Edición del contenido» | **No**: es un postprocesado de la descarga con capacidades de yt-dlp, no un editor | Necesidad | **A**: UC-02 A10, UC-03 A18, UC-15 A6; D-18 | Servicio externo y otra identidad del resultado · el User edita a mano |
| 13 | Partir por capítulos (visión, §6.3) | Un archivo por capítulo de un curso o audiolibro · User | S, K, Y | No | «Edición del contenido» | **No** | Necesidad | **A**: UC-02 A11, UC-03 A17; D-15 y D-18 | Varios resultados por job (§13.1) · el User corta a mano |
| 14 | `parse-metadata` (§6.3) | Metadatos correctos para organizar la biblioteca · User | S, Y | No | «Edición del contenido» | **No** | Necesidad | **A**: UC-02 A7, UC-24 A8 | Reglas validadas, sin comandos · metadatos inconsistentes |
| 15 | Plantillas de comandos personalizados (visión, §6.3) | Reutilizar preferencias · User | S, K | Opciones por invocación | «Interfaz de la CLI de yt-dlp; rompe las pruebas de contrato» | Sí para ejecutar comandos; **no** para la necesidad | Solución | **N**: UC-18; **M**: ejecutar comandos | Perfiles validados · repetir opciones en cada `enqueue` |
| 16 | Fragmentos concurrentes (§6.1, §6.3) | Descargas más rápidas · User | S, K, Y | 1 fragmento | Más peticiones al sitio | Parcialmente: se configura con BR-02 en cuenta | Necesidad | **R**: SUP-P09 | Más carga sobre el sitio · descargas HLS o DASH más lentas |
| 17 | aria2c (visión, §6.3) | Igual que 16 | S, K | — | Otra dependencia | Sí | Tecnología | **T**: SUP-P09 | — |
| 18 | Red medida (§6.3) | No consumir datos de una conexión de uso medido · User | S | No | «Propia de Android» | **No**: Windows tiene conexiones de uso medido | Necesidad | **A**: UC-21 A9 | Consulta a Windows · descargas con datos caros |
| 19 | Tarjeta SD (§6.3) | Elegir la unidad de destino · User | S | `download_directory` | Propia de Android | Sí: ya satisfecha | Duplicada | **M** | — |
| 20 | Notificaciones móviles (§6.3) | Enterarse de los sucesos sin vigilar · User | S | Resumen en la consola | Propia de Android | Sí para el canal móvil; **no** para la necesidad | Necesidad y canal | **N**: UC-28; D-14 | Un consumidor de los job events · el User vigila la consola |
| 21 | Exportar e importar el historial (§6.1, §6.3) | Trasladar o conservar la cola · User, Programa cliente | S | No | «La cola no es un historial» | **No**: los jobs terminados ya son un historial | Necesidad | **N**: UC-22 | Formato versionado · copiar la base de datos, con sus riesgos (UC-06 A8) |
| 22 | Modo privado (§6.3) | No conservar el registro de lo descargado · User | S | `purge` manual | «`purge` ya lo limpia» | Parcialmente | Necesidad | **A**: UC-10 A6 | Purga automática · purgar a mano |
| 23 | Búsqueda en YouTube (§6.3, como «fuera del dominio») | Encontrar un contenido antes de tener su URL · User | V, Y (`ytsearch`) | No | Se confundió con la búsqueda de voces de VoiceStudio | **No** | Necesidad | **A**: UC-15 A5 (se consolida; no es un caso de uso propio) | Una petición al sitio · el User busca en el navegador |
| 24 | Recortes de voz (§6.3) | Clip de voz para clonar | V | — | Fuera del dominio | Sí | Producto de voz | **M**; la necesidad genérica de un tramo es UC-02 A8 | — |
| 25 | Caché por hash del contenido (§6.3) | No repetir procesamientos | V | Duplicados por media key | Duplica BR-13 | Sí | Duplicada | **M**; la identidad es BR-32 | — |
| 26 | Red privada bloqueada (§6.3) | Evitar SSRF en un servidor | V, B | — | El producto es local | Sí | No aplica | **M** | — |
| 27 | Empezar la cola a una hora (§4.1, modelo §4.2) | Descargar en horarios permitidos sin estar presente · User | — | No | «Lo cubre el Programador de tareas de Windows» | **No**: no ofrece ventanas ni las combina con la pausa y los aplazamientos | Necesidad | **N**: UC-21; D-13 | Admisión por ventana · el User programa `run` y lo detiene a mano |
| 28 | Avisar al terminar (§4.1, modelo §4.2) | Igual que 20 | S | Resumen en la consola | «`run` ya resume al terminar» | **No** | Necesidad | **N**: UC-28 | Igual que 20 |
| 29 | Unir a otro contenedor, mkv (§6.1, «de momento») | Un contenedor compatible con el reproductor del User · User | S, K, Y | Contenedor del selector | Sin necesidad del User | **No** | Necesidad | **A**: UC-02 A14 | Remux sin pérdida · el User remuxa a mano |
| 30 | Forzar IPv4 y agente de usuario (§6.1, «de momento») | Conectar en redes con IPv6 roto · User | S, Y | No | Sin necesidad del User | IPv4: **no**; agente: sí | IPv4: necesidad; agente: mecanismo | **A**: UC-20 A7 (IPv4); **M**: agente de usuario (BR-12) | Una clave de configuración · fallos de red sin solución |
| 31 | `--download-archive` (§6.1, ADR-0012) | No volver a descargar lo ya descargado · User | S, Y | Solo detecta los activos; uno ya descargado acaba `FAILED` por su reclamación | ADR-0012 | Sí para la tecnología; la necesidad quedó **sin cubrir** | Tecnología y necesidad | **T**; la necesidad es BR-32 y D-16 (omitir como «ya descargado») | Identidad persistente · fallos confusos al volver a encolar |
| 32 | `CREATE_NO_WINDOW` (§6.1, «no aplica») | — | V | Programa de consola | Los workers comparten la consola | Sí | Técnica | **M** | — |
| 33 | Cuenta del sitio (visión 1.0, §4.1) | Acceso autorizado a lo que el User puede ver · User | S, K, V, B, D | No | D-1 | Pendiente | Necesidad | **N**: UC-19 (condicionado a D-1) | Ciclo de vida de credenciales · contenido autorizado inaccesible |
| 34 | Proxy (visión 1.0) | Salir por el proxy de la red · User | Todas | Proxy del sistema, sin diagnóstico | D-7 | Pendiente | Necesidad | **N**: UC-19 A1; **A**: UC-01 A11 (condicionados a D-7) | Credenciales de proxy · sin diagnóstico |
| 35 | Escenarios excluidos de los planes E1 y E2 | — | — | — | Secuencia de iteraciones | — | Planificación | **L**: no excluye necesidades | — |
| 36 | Alternativas descartadas en ADR-0005, 0017, 0029, 0030 y 0031 | — | — | — | Diseño | — | Alternativas técnicas | **L** | — |

### 12.2 Resultado

| Concepto | Cantidad | Filas |
|---|---:|---|
| Localizadas | 36 | 1–36 |
| No eran exclusiones de alcance (L) | 2 | 35, 36 |
| Exclusiones de alcance revisadas | 34 | 1–34 |
| Se mantienen justificadamente (M) | 9 | 2, 6, 7, 8, 19, 24, 25, 26, 32 |
| Solo tecnologías (T) | 3 | 11, 17, 31 |
| Interfaces diferidas (I) | 2 | 1, 9 |
| Decisiones de soporte o distribución (P) | 2 | 3, 4 |
| Reincorporadas como necesidad | 18 | 5, 10, 12–16, 18, 20–23, 27–30, 33, 34 |
| … que amplían casos de uso existentes | 9 | 5, 12, 13, 14, 18, 22, 23, 29, 30 |
| … que justifican casos de uso nuevos | 8 filas, 6 casos de uso | 10 (UC-24), 15 (UC-18), 20 y 28 (UC-28), 21 (UC-22), 27 (UC-21), 33 y 34 (UC-19) |
| … como requisito suplementario | 1 | 16 (SUP-P09); además, 5 y 9 aportan SUP-M01 y SUP-I01 |
| Que dependen de una decisión | 10 | 5, 9, 12, 13, 20, 27, 28, 31, 33, 34 |
| Sin cualificar | 0 | — |

Inconsistencias corregidas:
- la visión excluía la recodificación con un dato falso;
- la visión excluía SponsorBlock y los capítulos mientras UC-02 A7 seguía pendiente de cualificación;
- el MCP se excluía con un argumento («JSON cubre la automatización») que solo valía para dos comandos;
- «leer transcripciones» se excluía a la vez que «obtener información complementaria» quedaba pendiente.

### 12.3 Objetivos candidatos

| Candidato | Resultado |
|---|---|
| Administrar perfiles de descarga | UC-18 |
| Administrar perfiles de acceso autorizado | UC-19 (condicionado a D-1 y D-7) |
| Administrar la configuración | UC-20 |
| Programar la ejecución de la cola | UC-21 |
| Exportar la cola y el historial; importarlos | **Consolidados** en UC-22: el mismo objetivo (trasladar), en dos sentidos |
| Respaldar y restaurar la cola | UC-23: otro objetivo (recuperar la misma instalación) |
| Obtener la información complementaria | UC-24 |
| Administrar los resultados descargados | UC-25 |
| Verificar los resultados descargados | UC-26: separado de UC-25 porque es de solo lectura y lo reutilizan UC-06 y UC-25 |
| Buscar contenidos | **Consolidado** en UC-15 A5: el objetivo es el de UC-15 (saber qué encolar) |
| Administrar las dependencias multimedia | UC-27 (condicionado a D-8); sustituye al candidato «Actualizar yt-dlp» |
| Administrar las preferencias de avisos | UC-28 (recibir avisos); las preferencias son configuración (UC-20) |
| Integración programática | **No es un caso de uso**: es un canal hacia los casos de uso existentes (SUP-I01, D-17) |

## 13. Contratos transversales

### 13.1 Resultados de un job y su cardinalidad

**El modelo actual supone un archivo por job:**
- `Job.output_path` es una sola ruta, y `Job.complete` exige una ruta para `DOWNLOAD` y ninguna para `EXPANSION`;
- `JobCompleted(output_path)` lleva una sola ruta;
- la tabla `jobs` tiene una columna `output_path` con el índice único `unique_output_path` (migración 0003);
- la reclamación protege un nombre base sin extensión (`canonical_stem_path`, `existing_files_with_stem`).

**Contraste con las nuevas capacidades:**

| Escenario | Archivos | ¿Lo cubre el contrato actual? |
|---|---|---|
| Video y audio unidos | 1 (los formatos separados son parciales) | Sí |
| Solo audio | 1 | Sí |
| Con subtítulos, miniatura, descripción, `info.json` | 1 multimedia y N complementarios con otro nombre base (`título.es.vtt`, `título.info.json`) | **No**: solo se registra y se reclama el principal; `splitext` da un nombre base distinto (`título.es`), así que los complementarios quedan sin reclamación |
| Capítulos o secciones | N multimedia, con o sin el completo | **No** |
| Solo información (UC-24) | 0 multimedia y N complementarios | **No**: `Job.complete` exige una ruta |
| Resultados opcionales que el sitio no ofrece | Variable | **No**: no hay noción de opcional |

**Contrato funcional propuesto** (BR-29 a BR-31; sin elegir todavía la representación, que es D-15):
- **Qué es un resultado:** cada archivo producido por la petición, con su tipo y su obligatoriedad (BR-29).
- **Qué es completar:** todos los obligatorios publicados, propios y con contenido (BR-30). Un opcional ausente deja un aviso; un obligatorio que falla deja `FAILED` y conserva los resultados publicados.
- **Propiedad:** una reclamación por resultado (BR-31), sin apropiarse nunca de archivos ajenos (BR-17).
- **Integridad:** la verificación es por tipo (BR-38).
- **Cancelar durante el postprocesamiento:** se conserva lo publicado; lo no publicado es parcial (UC-05 A9). Publicar cada resultado es un movimiento atómico.
- **Recuperación:** la evidencia local se evalúa por resultado (UC-06 A12).
- **Reintento:** solo se produce lo que falta (UC-07 A8).
- **Un resultado que desaparece:** se informa y no cambia el estado (UC-25 A3).
- **Purga:** borra registros y nunca archivos (BR-18); con `--delete-files`, solo los resultados propios (UC-25 A1).

Relación: UC-03 A16 y A17, UC-05 A9, UC-06 A11 y A12, UC-07 A8, UC-09 A6, UC-10 A5, UC-17, UC-24, UC-25, UC-26; ADR-0030; D-5 (el espacio por job depende de N); D-9; D-11.

### 13.2 Identidad, variantes y duplicados

**Comportamiento actual (BR-13, migración 0002):** la identidad es la media key más «solo audio o no». Por eso:
- pedir el mismo video en 1080p y en 720p a la vez, o en dos carpetas, deja el segundo `SKIPPED`;
- volver a encolar algo ya descargado no se omite: el job falla `FILESYSTEM` contra la reclamación del primero, o contra su archivo si fue purgado (fila 31 del §12.1).

| Petición respecto de otra con la misma media key | Clasificación (BR-32) | Tratamiento propuesto |
|---|---|---|
| Misma especificación, una activa | Duplicado | `SKIPPED` (como hoy) |
| Misma especificación, la otra `COMPLETED` con sus resultados presentes | Ya descargado | `SKIPPED` con el motivo «ya descargado» y la ruta, en lugar de `FAILED` (D-16) |
| Otra calidad, contenedor, conversión, capítulos, segmentos o carpeta | Variante | Se descarga; si pide el mismo nombre final, decide la reclamación (BR-17) |
| Solo complementarios nuevos de un contenido descargado | Ampliación | UC-24 A5 |
| Mismo nombre final por la plantilla | Colisión de nombres | La reclamación decide; nunca se reemplaza sin autorización explícita (UC-25) |
| Reemplazo explícito de un resultado propio | Reemplazo autorizado | Solo con confirmación sobre un resultado propio (UC-25 A1, y después encolar) |

Se conservan las garantías de R-14 y de ADR-0030: la identidad nunca da la propiedad de un archivo.

**Identidades distintas** (conceptos; no implican cinco clases ni cinco tablas):

| Identidad | Identifica | Hoy |
|---|---|---|
| Del contenido (media identity) | El contenido remoto | `MediaKey` (extractor + id) |
| De la petición (request identity) | El resultado pedido | No existe: BR-13 usa la media key más «solo audio» |
| Del job | El trabajo persistido | `job_id` + `created_at` (owner token) |
| De cada resultado | Cada archivo producido | Solo `output_path` |
| De la propiedad | La autoridad sobre un resultado | Reclamación con el owner token |

**Efecto de cada opción en la identidad de la petición** (D-16):

| Efecto | Opciones | ¿En la identidad? |
|---|---|---|
| Cambia el resultado esperado | Selector o preajuste (normalizado), solo audio, contenedor, conversión, códecs, pistas, idiomas, subtítulos, capítulos, secciones, segmentos, transformaciones, complementarios pedidos | Sí |
| Cambia el destino | Carpeta de descargas y plantilla de salida (con la ruta normalizada como en ADR-0030) | Sí |
| Cambia la operación | Descarga o solo información (UC-24) | Sí |
| Cambia el acceso | Perfil de acceso, proxy | No. El resultado con acceso puede diferir (más calidad, contenido de miembros); el formato elegido se registra en el job (`selected_format_id`). Si el User quiere ambas variantes, las distingue por destino |
| Condiciones de ejecución | Timeout, reintentos, workers, ritmo, límite de ancho de banda, fragmentos | No |
| Observabilidad | Nivel de log, intervalo de progreso | No |

**Equivalencias:**
- **Normalización de rutas:** relativas y absolutas, mayúsculas en Windows y separadores (`realpath` + `normcase`).
- **Preajustes:** se traducen a su selector antes de calcular la identidad, así que un perfil o un preajuste equivalentes coinciden.
- **Orden y opciones desconocidas:** el orden no cuenta y las opciones desconocidas se rechazan al encolar.
- **Versión del algoritmo:** la identidad lleva la versión con la que se calculó; un cambio de algoritmo no convierte en duplicados los jobs anteriores.
- **Selectores:** se comparan por su texto normalizado; dos selectores distintos que acaban eligiendo el mismo formato no se detectan como duplicados.


### 13.3 SponsorBlock, capítulos y secciones

Capacidades de yt-dlp 2026.11.23:
- **Segmentos:** `SponsorBlockPP` consulta el servicio de SponsorBlock (por omisión `sponsor.ajay.app`, solo para YouTube y con un prefijo de 4 caracteres del SHA-256 del id del video). Un 404 significa «sin segmentos»; otros errores dan `PostProcessingError` tras `extractor_retries` intentos.
- **Marcar o quitar:** `ModifyChaptersPP` marca los segmentos como capítulos o los quita. Los quita concatenando con copia de streams; los cortes son exactos solo con `force_keyframes_at_cuts`, que recodifica.
- **Dividir:** `FFmpegSplitChaptersPP` divide por capítulos con copia de streams.
- **Secciones:** `download_ranges` descarga solo ciertos tramos.

**Tratamiento:**
- Marcar es una variante que conserva el contenido íntegro; quitar produce otro contenido y entra en la identidad (BR-32).
- Que no haya segmentos es un resultado normal; un fallo del servicio se decide en D-18.
- Al reanudar o reintentar, se vuelven a consultar los segmentos.
- Capítulos y secciones cambian la cardinalidad (§13.1) y las rutas: carpeta por contenido o sufijo por capítulo, siempre reclamados.

No es un editor multimedia: solo se aplican transformaciones que el User pide al encolar, con postprocessors de yt-dlp.

### 13.4 Recodificación y compatibilidad

La configuración de la build incluida (`n9.0.2-39`, BtbN, variante LGPL compartida), leída en `avcodec-63.dll`, sin ejecutar `ffmpeg.exe`:
- **Desactivados:** `libx264`, `libx265`, `libfdk-aac`.
- **Activados:**
  - `libopenh264` (H.264), `libkvazaar` (HEVC) y `libvvenc` (H.266);
  - `libvpx` (VP8 y VP9), `libaom`, `librav1e` y `libsvtav1` (AV1);
  - `libmp3lame`, `libopus`, `libvorbis` y el AAC nativo;
  - codificadores por hardware (`ffnvcodec`, `amf`, `libvpl`).

**Conclusión:** la exclusión de la visión («la build LGPL no incluye codificadores H.264/H.265») era falsa. Escalera de compatibilidad (SUP-M01):
1. Elegir formatos compatibles del sitio.
2. Unir o cambiar de contenedor sin pérdida.
3. Convertir el audio.
4. Recodificar el video solo si se pide.

**Pendiente:**
- comprobar con `ffmpeg -encoders` en Windows (campaña);
- la calidad de `libopenh264` y de `mpeg4` frente a `libx264`;
- el licenciamiento de patentes de H.264 y HEVC (R-29).

Todo esto lo decide D-18. No se cambia la build.

### 13.5 Configuración, perfiles y acceso

Precedencia vigente: argumentos, variables de entorno, `config.toml`, valores por defecto (SUP-F03). Se separan cuatro clases de información:
- **configuración:** UC-20;
- **perfiles:** UC-18, con las opciones copiadas en el job al encolar (BR-33);
- **credenciales:** UC-19, solo referencias (BR-34) y copias por job (BR-35);
- **estado operativo:** pausa, aplazamientos y programación, que no se guardan en `config.toml`.

Si las opciones se resolvieran al ejecutar en lugar de al encolar, un job recuperado tras un cierre podría descargar con otras opciones que las pedidas. Por eso la recomendación de D-19 es fijarlas al encolar.

### 13.6 Optimización y ancho de banda

Capacidades de yt-dlp, todas por instancia de `YoutubeDL`, es decir, por worker:
- `concurrent_fragment_downloads`;
- `ratelimit` y `throttledratelimit`;
- `http_chunk_size`;
- `retries`, `fragment_retries`, `file_access_retries` y `extractor_retries`;
- `retry_sleep_functions`;
- `socket_timeout`;
- `max_filesize` y `min_filesize`;
- `continuedl`.

| Dimensión | Hoy | Propuesta |
|---|---|---|
| Concurrencia total de peticiones | `worker_count` × 1 fragmento | `worker_count` × `concurrent_fragments` (SUP-P09), con BR-02 |
| Límite por job | No | `rate_limit` (SUP-P06) |
| Límite global | No | D-20: repartir entre los workers activos o fijar el límite por worker |
| Reintentos | 0 HTTP y 0 de fragmentos (R-24) | BR-07 y SUP-R11 |
| Tamaño máximo | No | `max_filesize` como opción de perfil (UC-18), si el User lo necesita |

aria2c sigue excluido como tecnología: no hay ninguna necesidad que yt-dlp no cubra. No se crea un descargador propio.

### 13.7 Integración programática

**Necesidad:** que otros programas encolen, consulten, cancelen, reintenten, controlen la ejecución, lean el progreso, los sucesos y los errores, y diagnostiquen, sin interpretar texto. Se distinguen:
- **contrato:** salida JSON, errores estructurados, códigos de salida y versionado (SUP-I01);
- **canal adicional:** biblioteca Python, API HTTP o MCP (D-17).

No se crean casos de uso por canal: todos los canales usan los servicios de aplicación ya separados (`job_queue`, ADR-0001). La salida JSON propuesta en `list` y `show` es una parte del contrato, no el contrato completo.

**Modelo de confianza por interfaz** (revisa la exclusión de «red privada bloqueada», fila 26 del §12.1):

| Origen de la entrada | Confianza | Tratamiento |
|---|---|---|
| User local en la CLI | Alta | Se aceptan URLs locales y privadas (pruebas controladas, servidores propios) |
| Aplicación local autorizada (CLI con JSON) | Alta, con los permisos del usuario | Igual que la CLI |
| Datos importados (UC-22) y respaldos (UC-23) | Baja | Validación de esquema y versión, rutas dentro del destino, sin propiedad (SUP-SEC05) |
| Automatizaciones (programación, UC-21) | Las de quien las configuró | Igual que la CLI |
| Consumidores remotos futuros (API HTTP, MCP) | Baja | Solo en `127.0.0.1` y con URLs privadas restringidas por defecto; se decide al diseñar esa interfaz (D-17) |
| Redirecciones del sitio | Las gestiona yt-dlp | Sin cambio |

La fila 26 se mantiene excluida para la CLI y queda **condicionada** para las interfaces remotas futuras.

### 13.8 Defectos, divergencias, ampliaciones y riesgos

| Elemento | Clasificación | Escenario afectado | Motivo |
|---|---|---|---|
| R-24 (0 reintentos HTTP y de fragmentos) | **Divergencia** del reparto documentado (los reintentos dentro de un job son de yt-dlp) | UC-03 A15 | Ningún contrato aprobado prometía reintentos, pero el diseño los delegaba en yt-dlp y hoy no ocurren |
| R-25 (la recuperación depende del sitio) | **Defecto** de un escenario vigente | UC-06 A4 | A4 promete completar sin descargar de nuevo, y no lo hace si el sitio no responde |
| R-28 (fallos de almacenamiento como `UNKNOWN`) | **Defecto** de un escenario vigente | UC-03 A2 | El motivo `FILESYSTEM` existe y la clasificación promete el motivo |
| R-26 (directos) | Decisión pendiente (D-10) | UC-03 E1 | Comportamiento no definido |
| R-27 (fuga de credenciales) | Riesgo condicionado | UC-19 | Solo si se adoptan credenciales |
| R-20 a R-23 | Riesgos | UC-11, UC-17, VUC | — |
| R-29 (patentes de los códecs) | Riesgo condicionado | UC-03 A19 | Solo si se adopta la recodificación |
| R-30 (complementarios sin reclamación) | Riesgo de las ampliaciones | UC-03 A16, UC-24 | Solo si se implementan antes de D-15 |
| T42-D1 a D12 | Defectos corregidos, pendientes de confirmar en Windows | Varios | [Registro de T42](../project-management/t42-results.md) |
| UC-03 A1 con variantes | Limitación de un escenario vigente | UC-03 A1 | BR-13 aplicado a variantes; D-16 |

### 13.9 Gobierno de los identificadores

- **UC-12:** retirado, fusionado en UC-11 A2.
- **UC-13:** retirado. Su objetivo («esperar espacio en disco») describía una solución.
- **UC-17:** no reactiva UC-13. Es una responsabilidad nueva y mayor: todas las condiciones de almacenamiento, con escenarios preventivos y reactivos, y no todas se resuelven esperando. Reactivar UC-13 habría mantenido un identificador cuyo significado histórico era «esperar». La relación queda registrada en UC-17 (historial), en el modelo (UC-13: «sustituido por UC-17») y en §4.3.
- **UC-18 a UC-28:** se asignaron después de cualificar cada objetivo.
- **Consolidados en UC-15 y en UC-22:** dos candidatos (buscar contenidos; exportar e importar).
- **Integración programática:** no recibió identificador, porque no es un caso de uso (§12.3).

No se renumeró ningún caso de uso.

### 13.10 Relación entre decisiones

```mermaid
---
config:
  theme: base
  darkMode: true
  themeVariables:
    background:         "#0f172a"
    primaryColor:       "#1e293b"
    primaryTextColor:   "#f1f5f9"
    primaryBorderColor: "#94a3b8"
    lineColor:          "#cbd5e1"
    secondaryColor:     "#334155"
    tertiaryColor:      "#1e3a8a"
    noteBkgColor:       "#1e3a8a"
    noteTextColor:      "#f1f5f9"
---
flowchart TD
    ProfilesD19["D-19 Perfiles"] --> IdentityD16["D-16 Identidad"]
    TransformsD18["D-18 Transformaciones"] --> IdentityD16
    IdentityD16 --> ResultsD15["D-15 Resultados"]
    TransformsD18 --> ResultsD15
    ResultsD15 --> FilesD11["D-11 Propiedad y archivos"]
    ResultsD15 --> RecoveryD9["D-9 Recuperación"]
    ResultsD15 --> StorageD5["D-5 Almacenamiento"]
    StorageD5 --> StorageFailuresD12["D-12 Fallos de almacenamiento"]
    StorageFailuresD12 --> ContinuityD2["D-2 Continuidad"]
    AccessD1D7["D-1 y D-7 Acceso"] --> ContinuityD2
    AccessD1D7 --> ProfilesD19
    PacingD3D4["D-3 y D-4 Ritmo y restricciones"] --> ContinuityD2
    ContinuityD2 --> PauseD6["D-6 Pausa"]
    PauseD6 --> ScheduleD13["D-13 Programación"]
    BandwidthD20["D-20 Ancho de banda"] --> ContinuityD2
    DependenciesD8["D-8 Dependencias"] --> ResultsD15
    DependenciesD8 --> TransformsD18
    LiveD10["D-10 Directos"] --> ScheduleD13
    LiveD10 --> StorageD5
    IntegrationD17["D-17 Integración"] --> PauseD6
    ContinuityD2 --> NotificationsD14["D-14 Avisos"]
    RecoveryD9 --> NotificationsD14
    RetentionD21["D-21 Retención"] --> FilesD11
    RecoveryD9 --> FilesD11

    classDef default fill:#1e293b,stroke:#94a3b8,stroke-width:1px,color:#f1f5f9
    classDef cluster fill:#1e3a8a,stroke:#94a3b8,stroke-width:1px,color:#f1f5f9
    classDef focal fill:#1e3a8a,stroke:#60a5fa,color:#f1f5f9
    class ResultsD15,IdentityD16 focal
```

Conciliado con los contratos reales; sobre el diagrama preliminar de la instrucción:
- **Añadidos:**
  - D-1 y D-7 → D-19: los perfiles referencian el acceso;
  - D-8 → D-18: cambiar ffmpeg o yt-dlp cambia las transformaciones;
  - D-10 → D-5: los directos reservan espacio;
  - D-21 → D-11: la retención afecta a la propiedad;
  - D-9 → D-11: reutilizar exige el mismo nivel de evidencia que mover.
- **Ciclos:** ninguno. D-15 y D-16 son los nodos de los que dependen más decisiones y deben diseñarse primero.
- **Condiciones compartidas que podrían contradecirse:**
  - **D-2 y D-6:** una cola en pausa y con una condición externa a la vez; prevalece la intención del User.
  - **D-13 y D-2:** una ventana que se cierra durante un aplazamiento; la ventana solo impide el envío.
  - **D-18 y D-15:** un servicio auxiliar caído deja un resultado pedido sin hacer; se resuelve como condición externa (§13.16).

**Interdependencias en texto** (para lectores sin Mermaid):

| Decisiones | Relación |
|---|---|
| D-1, D-7, D-19 | Configuración y seguridad del acceso (UC-19, UC-18): referencias, copias por job, perfiles fijados al encolar |
| D-2, D-6, D-13 | Continuidad de la ejecución: política ante condiciones, pausa y ventanas comparten la admisión de `run` |
| D-2, D-12 | Tratamiento de los jobs afectados por el almacenamiento |
| D-5, D-15 | El espacio por job depende de cuántos resultados produce |
| D-9, D-11, D-15, D-16 | Propiedad, integridad e identidad de los resultados |
| D-8, D-18 | Cambiar yt-dlp o ffmpeg cambia los contratos de extracción y postprocesamiento |
| D-14, D-17 | Los avisos y el canal programático consumen los mismos sucesos |
| D-3, D-20 | Ritmo de peticiones y ancho de banda global |

### 13.11 Fronteras de interrupción y evidencia durable (D-9)

| Interrupción | Evidencia durable que existe hoy | Reconciliación recomendada |
|---|---|---|
| Antes de iniciar la descarga | Job `RUNNING` en SQLite | Recuperar a `PENDING` (BR-19); vigente |
| Durante la descarga o la escritura de parciales | `.part`, `.ytdl` en la carpeta de parciales | Reanudar con `continuedl` (UC-06); vigente |
| Durante la unión o el postprocesamiento | Formatos separados en la carpeta de parciales; archivo de salida incompleto de ffmpeg | Repetir el postprocesamiento sin descargar; el incompleto nunca se publica (está en la carpeta de parciales) |
| Durante la publicación (movimiento a la carpeta final) | Reclamación creada antes de descargar; archivo en la carpeta de parciales o ya movido | El movimiento es un renombrado en la misma unidad (la carpeta de parciales está dentro de la de descargas): o el archivo está entero en su ruta final, o sigue en parciales |
| Tras publicar uno de N resultados | Reclamaciones y archivos publicados | Por resultado: publicado, propio y estructuralmente correcto se reutiliza; el resto se produce (UC-06 A12) |
| Tras publicar todos, antes de emitir `JobCompleted` | Todos publicados; job `RUNNING` | Hoy: R-25. Recomendado: completar con la evidencia local (BR-23), sin peticiones |
| Tras emitir `JobCompleted`, antes de guardarlo | Igual que la fila anterior (el evento viaja por una cola en memoria) | Igual |
| Durante una transacción SQLite | El journal WAL deshace la transacción incompleta | Estado anterior coherente; continúa como alguna de las filas anteriores |
| Durante una restauración (UC-23) | Estado anterior renombrado como copia | Volver al estado anterior; UC-23 E1 y E2 |

**Evidencia que falta y que el diseño deberá añadir:**
- la expectativa de cada resultado (tipo, streams y duración esperados), registrada antes de publicar;
- la marca de publicado por resultado.

Sin ellas, la evidencia local solo demuestra la propiedad, no la integridad (la propiedad no equivale a integridad).

### 13.12 Nivel de evidencia por operación sobre un resultado (D-11)

| Operación | Riesgo | Evidencia exigida |
|---|---|---|
| Consultar (UC-09, UC-25) | Ninguno | Registro del resultado; existencia en el disco, informada |
| Reutilizar en recuperación o reintento (UC-06, UC-07) | Dar por bueno un archivo dañado o ajeno | Registro, reclamación con owner token y verificación estructural (BR-38) |
| Verificar (UC-26) | Ninguno (solo lectura) | La verificación misma |
| Mover (UC-25 A6) | Romper la protección | Lo anterior, más que no haya cambiado desde la publicación (tamaño y fecha; hash si se registró) y el movimiento conjunto del archivo y su reclamación |
| Eliminar (UC-25 A1) | Pérdida de datos | Lo anterior, más vista previa y confirmación explícita; con `--force`, se borra aunque haya cambiado, solo si es propio |
| Sobrescribir | Pérdida de datos | Nunca, salvo un reemplazo autorizado de un resultado propio (§13.2) |

Un archivo no es propio por estar en la carpeta de descargas, coincidir con la plantilla, compartir el nombre base, tener una ruta registrada, tener el mismo tamaño o haber tenido una reclamación en el pasado.

Si el User u otro programa sustituye un resultado tras completarse, el registro deja de coincidir:
- consultar y verificar lo informan;
- reutilizar, mover y eliminar lo rechazan, salvo con `--force` sobre uno propio.

### 13.13 Ciclo de vida: estados, elegibilidad y condiciones

Sin estados nuevos de job. Las demás dimensiones se representan con datos y políticas:

| Dimensión | Representación |
|---|---|
| Estado del job | `JobStatus` vigente (§1.1 del vocabulario) |
| Estado de ejecución | `RUNNING` y el worker asignado (vigente) |
| Estado de un resultado (D-15) | No pedido, pedido obligatorio, pedido opcional, en proceso, publicado, fallido, ausente al consultar, no verificable |
| Elegibilidad para el envío | Se calcula en la admisión de `run` a partir de la condición, la pausa, la ventana, el tiempo de publicación de un directo y los recursos. No se guarda como estado |
| Intención del User | Job requests (cancelar, reintentar, pausar, continuar, detener); la pausa se guarda (D-6) |
| Condición externa | Datos de la condición: tipo, alcance, desde cuándo y, si la hay, la hora de continuación (`Retry-After`) |
| Resultado de verificación | Informe de UC-26; no cambia el estado del job |

```mermaid
---
config:
  theme: base
  darkMode: true
  themeVariables:
    background:               "#0f172a"
    primaryColor:             "#1e293b"
    primaryTextColor:         "#f1f5f9"
    primaryBorderColor:       "#94a3b8"
    lineColor:                "#cbd5e1"
    secondaryColor:           "#334155"
    tertiaryColor:            "#1e3a8a"
    noteBkgColor:             "#1e3a8a"
    noteTextColor:            "#f1f5f9"
    specialStateColor:        "#f1f5f9"
    compositeBackground:      "#162032"
    compositeTitleBackground: "#1e293b"
---
stateDiagram-v2
    [*] --> PENDING : enqueue, import
    PENDING --> RUNNING : admitted by run
    PENDING --> PENDING : not eligible (condition, pause, window, upcoming live)
    PENDING --> CANCELLED : cancel
    RUNNING --> PENDING : deferred by an external condition, or interrupted and recovered
    RUNNING --> CANCELLATION_REQUESTED : cancel
    CANCELLATION_REQUESTED --> CANCELLED : worker stopped
    RUNNING --> COMPLETED : all required results published
    RUNNING --> FAILED : a required result failed
    RUNNING --> SKIPPED : duplicate or already downloaded
    FAILED --> PENDING : retry
    CANCELLED --> PENDING : retry
    COMPLETED --> [*] : purge
    CANCELLED --> [*] : purge
```

Un job con N resultados, una condición externa y una cancelación a la vez:
- la cancelación prevalece y conserva los resultados ya publicados (UC-05 A9);
- la condición externa nunca convierte un job en `FAILED`;
- `RUNNING → PENDING` por un aplazamiento no gasta intentos (BR-04).

### 13.14 Privacidad y retención (D-21)

| Dato | Obligatorio para operar | Retención recomendada | Protección | Efecto de borrarlo |
|---|---|---|---|---|
| Jobs activos | Sí | Hasta terminar | — | Pérdida de trabajo |
| Historial (jobs terminados) | No | Configurable (UC-10 A6; plazo pendiente, D-21) | — | Se pierde la trazabilidad; los resultados siguen protegidos por sus reclamaciones mientras existan; purgar suelta las de jobs inexistentes |
| Reclamaciones | Sí, mientras el job sea dueño | Mientras exista el job | — | Archivos sin protección frente a otros jobs |
| Parciales | Sí, para reanudar | Hasta completar, cancelar o purgar | — | Descargar de nuevo |
| Resultados | Del User | Del User (UC-25) | Propiedad | — |
| Logs | No | Rotación vigente (5 MB × 3) | Sin secretos (SUP-SEC01) | Menos diagnóstico |
| Caché de yt-dlp | No | Regenerable | — | Más peticiones |
| Configuración y perfiles | Sí | Permanente | Sin secretos (BR-34) | Valores por defecto |
| Credenciales | Del User | Fuera del producto; copias temporales solo durante el job (BR-35) | ACL o modo 0600 | — |
| Respaldos y exportaciones | No | Del User | Sin secretos; se validan al usarlos (SUP-SEC05) | — |
| Evidencia de validación | No | Del Mantenedor | Sin multimedia ni secretos (SUP-SEC02) | — |

El «modo privado» (no conservar el registro de lo descargado) no equivale a la purga automática:
- la purga borra registros, pero los logs y la caché conservan rastros;
- un modo sin historial requiere además no registrar títulos ni URLs en el log.

Queda como alternativa de D-21.

### 13.15 Seguridad transversal

| Riesgo | Requisito existente o nuevo |
|---|---|
| Escritura fuera del destino autorizado (título con `..`, plantilla manipulada en una importación) | SUP-SEC06: toda ruta final se resuelve dentro de la carpeta de descargas, como ya garantiza `canonical_stem_path` con `realpath` |
| Colisiones, normalización y mayúsculas en Windows | ADR-0030 (`normcase`, `realpath`); vigente |
| Archivo sustituido tras completar | §13.12 |
| Enlaces simbólicos y uniones en la ruta | `realpath` y comprobación del volumen (`winerror` 448, catálogo §3) |
| Secretos en excepciones, logs, JSON e informes | SUP-SEC01: se enmascaran en el origen (D-7) |
| Datos importados y respaldos manipulados | SUP-SEC05: se validan contra el esquema y la versión antes de escribir nada; nunca conceden propiedad (BR-36) |
| Credenciales abandonadas tras una interrupción | BR-35, SUP-SEC04 |
| Avisos con información sensible | UC-28: sin secretos ni rutas completas de credenciales |

### 13.16 Contradicciones resueltas con las resoluciones aprobadas

| Contradicción | Resolución |
|---|---|
| BR-29 permitía completar un job de información con uno solo de los elementos pedidos | Todo lo pedido es obligatorio salvo marca explícita (BR-29 y BR-30, versión 3) |
| BR-29 trataba los complementarios como opcionales por omisión | Igual |
| UC-03 A18 completaba sin quitar segmentos si SponsorBlock fallaba | Es un resultado pedido: se conserva el multimedia y se repite el postprocesamiento |
| BR-13 (vigente en el código) frente a la resolución de D-16 | BR-13 queda como comportamiento actual, **divergente**; UC-03 A1 se marca divergente |
| BR-02 y BR-03 con 10–20 s y 60 minutos | Sin valores universales (D-3, D-4); parámetros pendientes |

### 13.17 Configuración efectiva

Precedencia vigente: argumentos, variables de entorno, `config.toml`, valores por defecto (SUP-F03). Los perfiles se insertan entre los argumentos y la configuración solo para las opciones de resultado:

| Clase | Origen | Cuándo se resuelve | ¿Forma parte de la identidad? |
|---|---|---|---|
| Resultado y postprocesamiento | Argumentos, perfil, configuración, valores por defecto | Al encolar (fijado en el job) | Sí |
| Destino | Igual | Al encolar | Sí |
| Acceso | Perfil de acceso por nombre | Al enviar el job | No (§13.2) |
| Operativa y recursos | Argumentos de `run`, variables de entorno, configuración | En cada `run` y en cada envío | No |
| Secretos | Archivos del User o almacén de credenciales | En cada uso | No |
| Estado operativo | Base de datos | Persistido | No |

**Validación:**
- al encolar: sintaxis, combinaciones y existencia de los perfiles;
- al enviar: el acceso existe y no ha caducado, el destino es utilizable (UC-17), y el codificador pedido está disponible.

Una opción válida al encolar puede dejar de serlo si cambia el entorno. Entonces el job falla con un motivo de configuración, sin aplazarse.

### 13.18 Respaldo, restauración e intercambio

**Responsabilidades:** se resuelven con D-9, D-11, D-15, D-16 y D-21, sin una decisión nueva.

**Alcance del respaldo (UC-23):**
- **Incluye:**
  - la base de datos, con su WAL integrado por la API de copia de seguridad;
  - las job requests pendientes y las reclamaciones con sus owner tokens;
  - la configuración y los perfiles;
  - las versiones del esquema y del programa.
- **No incluye:** parciales, resultados ni secretos.

**Evidencia:** el experimento `sqlite_backup` (5 copias íntegras y coherentes con escrituras concurrentes). Que SQLite esté íntegro no basta: las reclamaciones viven fuera de la base de datos. Por eso, al restaurar, la conciliación de UC-06 trata como ausente todo resultado cuya reclamación o archivo no coincida.

| Restauración | Comportamiento |
|---|---|
| Misma instalación | UC-23 A1 y A2 |
| Instalación vacía u otra máquina | Rutas distintas: los resultados que no existen se informan (UC-06 A9); nunca se reclama un archivo existente que no tenga reclamación propia |
| Versión antigua | Migraciones progresivas; ids reutilizados protegidos por el owner token (UC-06 A8) |
| Sobre una instalación con jobs | Se rechaza; para combinar está la importación (UC-22) |
| Interrumpida | El estado anterior sigue renombrado como copia: se vuelve a él |

**Intercambio (UC-22):**
- URLs, preferencias, perfiles, jobs, historial y relaciones de playlist;
- identidad de la petición para los duplicados;
- reconciliación de rutas (A4);
- formato versionado sin secretos (SUP-I02);
- los resultados solo como información, sin propiedad.

### 13.19 Recursos y métodos de evaluación

| Recurso | Requisito | Medible en Linux | Requiere Windows |
|---|---|---|---|
| Memoria del proceso principal y de los workers | SUP-P04 | Sí (referencia: unos 38 MB por proceso) | El presupuesto se fija en Windows |
| Espacio por job (unión, N resultados, recodificación) | SUP-P07, SUP-P08 | Sí, con medios locales de tamaño conocido | Confirmación |
| CPU de la recodificación y de la verificación con decodificación | SUP-M01, BR-38 | Sí | Codificadores por hardware |
| Ancho de banda agregado con N fragmentos | SUP-P06, SUP-P09, D-20 | Sí, con el servidor local y un límite | — |
| SQLite y WAL con colas largas | SUP-P08 | Sí | — |
| Directos de larga duración | D-10 | Parcial (HLS local sin final) | — |
| Suspensión del sistema | SUP-R08 | No | Sí |
| Reciclado de workers en operación prolongada | SUP-P02, `max_jobs_per_worker` | Sí | Confirmación |

Ningún valor se fija sin medición.

## 14. Impacto en la arquitectura (insumo para Analysis and Design)

| Componente (ADR-0017) | Contrato actual | Necesidad | Clasificación |
|---|---|---|---|
| `jobs` | `Job` con `output_path`; `DownloadOptions`; `MediaKey`; `JobStatus` | N resultados (D-15), identidad de la petición (D-16), condición de aplazamiento (D-2) | Generalizar un contrato |
| `job_storage` | Tabla `jobs`; índices `unique_active_download_per_media` y `unique_output_path`; migraciones 0001 a 0004 | Registro de resultados, identidad de la petición, estado de pausa y programación | Migraciones nuevas y progresivas; las publicadas no cambian |
| `job_queue` | `RunQueue`, admisión simple, job requests | Admisión por condición, ventana, pausa y directo programado; política `when_blocked`; ritmo por sitio | Ampliar una responsabilidad |
| `media_extraction` | Parámetros de yt-dlp, clasificador, reclamaciones, `FinalPathRecorder` | Reintentos (R-24), cadena de causas (R-28), postprocessors de D-18, una reclamación por resultado, copias de cookies, proxy, `Retry-After`, evidencia local (R-25) | Ampliar y generalizar; corregir defectos |
| `workers` | Pool de procesos, terminación de árboles (ADR-0029) | Pausa inmediata con el mecanismo existente; directos | Ya satisfecho en su mayoría |
| `diagnostics` | `diagnose` | Destino, proxy, dependencias, informe (UC-16), versiones (UC-27) | Ampliar |
| `configuration` | Precedencia SUP-F03 | Perfiles, acceso, avisos, ventanas, retención; `config show` con el origen | Ampliar |
| `command_line` | `argparse` y presentación | Comandos nuevos; JSON versionado; errores estructurados | Ampliar; la lógica queda en `job_queue` |
| `ffmpeg_discovery` | Verificación de ffmpeg y ffprobe | Codificadores disponibles (D-18), ffprobe para la verificación | Ampliar |

**Invariantes que deben preservarse:**
- solo el proceso de `run` cambia el estado (SUP-C04);
- los workers solo publican job events;
- ningún archivo ajeno se toca (ADR-0030, R-14);
- el owner token protege de ids reutilizados;
- el progreso no va a la base de datos (SUP-P03);
- las reglas de la cola se prueban sin yt-dlp, sin SQLite y sin procesos (SUP-S04).

**Eventos:** `JobCompleted` deberá llevar los resultados publicados. Hacen falta un evento de aplazamiento (ADR-0031) y uno de resultado publicado, o una forma equivalente. Su diseño corresponde a Analysis and Design.

### 14.1 Revisión de los ADR

| ADR | Situación |
|---|---|
| ADR-0001 (sin GUI) | Vigente; la nota de 2026-11-26 aclara que la GUI sigue diferida y que las necesidades se cubren con SUP-I01 |
| ADR-0002 (yt-dlp fijado) | Vigente; UC-27 lo respeta |
| ADR-0004 (Windows x64) | Vigente |
| ADR-0007, ADR-0018 (licencias, build LGPL) | Vigentes; D-18 añade la cuestión de patentes (R-29), no de licencia |
| ADR-0009 (expansión en jobs) | Vigente |
| ADR-0010 (cola en SQLite) | Vigente; necesitará ampliarse con los resultados y la identidad (nueva decisión en Analysis and Design) |
| ADR-0012 (sin `download_archive`) | Vigente para la tecnología; «ya descargado» se resuelve con D-16 |
| ADR-0013, ADR-0029 (árbol de procesos) | Vigentes; los reutilizan la pausa inmediata y los directos |
| ADR-0017 (API pública y dependencias) | Vigente; la API Python de D-17 se apoya en él |
| ADR-0030 (reclamaciones) | Vigente en su principio; necesita ampliarse a una reclamación por resultado (nueva decisión que lo complemente, sin cambiar su significado) |
| ADR-0031 (aplazar ante condiciones externas, propuesta) | Debe revisarse con D-2, D-3, D-4 y D-12: sus valores fijos (60 min, 10–20 s) quedan sustituidos por los parámetros pendientes |
| Nuevas decisiones de diseño previstas | Modelo de resultados (D-15 y D-16), admisión y política de continuidad (D-2, D-6, D-13, D-20), acceso y secretos (D-1, D-7), contrato programático (D-17). Cuatro decisiones de diseño, no veinte ADR |

### 14.2 Cobertura de las tareas candidatas

| Tarea | Cobertura respecto de los 26 casos de uso | Situación |
|---|---|---|
| T52 aplazar y reconocer condiciones | UC-11, UC-17 | Depende de D-2 y D-12; se consolida con T67 |
| T53 continuidad y admisión | UC-11, UC-14, UC-21 | Ampliar: la admisión es común a las ventanas, la pausa y los directos |
| T54 reintentos de yt-dlp | UC-03 A15 (R-24) | Aplicable sin dependencias: corrige una divergencia |
| T55 evidencia local | UC-06 A4, A11 y A12 (R-25) | Depende de D-15 (registro de la expectativa) |
| T56 `list`, `show` y `diagnose` | UC-01, UC-08, UC-09 | Se superpone con SUP-I01; consolidar |
| T57 suspensión | SUP-R08 | Aplicable |
| T58 pausa y ancho de banda | UC-14, D-20 | Ampliar con el límite global |
| T59 a T61 validación | VUC-04 a VUC-08, UC-16 | Aplicables |
| T62 consulta y selección | UC-15, UC-02 A6 y UC-04 A8 | Aplicable |
| T63 indicación de reintento | SUP-U05 | Aplicable |
| T64 informe | UC-16 | Aplicable |
| T65 directos y purgar con archivos | D-10, UC-10 A5 y UC-25 | Ampliar con D-10 y UC-25 |
| T66 preajustes, JSON y búsqueda | UC-02 A9, UC-08, UC-09, SUP-I01 | Consolidar con T56 |
| T67 almacenamiento | UC-17 (R-28) | Consolidar con T52 |
| Sin tarea | UC-18 a UC-28, D-15, D-16, D-18 | Se descompondrán después de Analysis and Design, por responsabilidades comunes (modelo de resultados, admisión, acceso, contrato programático) |

**Defectos que requieren un tratamiento explícito:** R-25 y R-28, y la divergencia R-24. Sus criterios de regresión están en D-9, D-12 y D-3.

## Fuentes

- IIBA, *A Guide to the Business Analysis Body of Knowledge (BABOK Guide)* v3, copia entregada por el Responsable: capítulos 6, 7 y 10.
- Wiki de yt-dlp, *Extractors* y *PO-Token-Guide*: texto entregado por el Responsable el 2026-11-26.
- yt-dlp 2026.11.23: `yt_dlp/options.py`, `yt_dlp/__init__.py`, `yt_dlp/YoutubeDL.py`, `yt_dlp/utils/_utils.py` (`RetryManager`), `yt_dlp/networking/`, `yt_dlp/extractor/youtube/_video.py` y `_base.py`, `yt_dlp/extractor/common.py` (`raise_no_formats`).
- Seal `5a4f5fb`, VoiceStudio `d9061408`, VoiceBlueprintPro `e9a2a63`, YTDownload-2026 `0abda8e`, Kannagi (`upstream/source/yt-dlp-gui-kannagi`), FFmpeg `329157f5` y n9.0.2-39: rutas en §5.1 y §6.1.
- Consolas y evidencia de la ejecución `20261125-222227-ddffe96cb470` ([registro de la campaña](../project-management/t42-results.md)).
- Historial: el análisis detallado de VoiceStudio (flujos, actores y trazabilidad) se publicó en `doc/requirements/benchmarking/voicestudio-use-cases.md` (commit `14bd247`) y se integró aquí y en los artefactos canónicos; el archivo se retiró en esta versión.
