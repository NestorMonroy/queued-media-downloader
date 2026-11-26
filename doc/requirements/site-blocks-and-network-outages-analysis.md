# Análisis: bloqueos del sitio y cortes de red

- **Fase RUP:** Elaboración (cambio de requisitos tras la campaña T42)
- **Versión:** 1.0 (propuesta para revisión del Responsable)
- **Fecha:** 2026-11-26
- **Técnicas (BABOK v3):** 10.34 Process Analysis (eficiencia del proceso y desperdicio), 10.40 Root Cause Analysis
- **Casos de uso nuevos:** [UC-11](use-cases/uc-11-wait-out-a-site-block.md), [UC-12](use-cases/uc-12-wait-for-the-network.md)
- **Decisión de diseño propuesta:** [ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md)

---

## 1. Problema

| | |
|---|---|
| **El problema de** | una cola que sigue enviando jobs cuando el sitio bloquea las peticiones o el equipo pierde la conexión |
| **afecta a** | el User, que deja la cola trabajando sin vigilarla, y al Evaluador de la campaña de Windows |
| **cuyo impacto es** | jobs sanos marcados `FAILED` en segundos, peticiones que siguen llegando a un sitio que ya bloqueó (y pueden alargar el bloqueo), y horas de trabajo manual: notar los fallos, esperar, `retry --all-failed`, volver a ejecutar y volver a comprobar |
| **una solución exitosa** | reduce el ritmo de peticiones antes de llegar al bloqueo; ante un bloqueo o un corte, deja los jobs en la cola sin gastarlos, espera y continúa sola, y dice qué espera y hasta cuándo |

**Restricción del Responsable (2026-11-26):** no depender de PO Tokens. La solución no usa proveedores de PO Token ni extractor args de clientes que los requieran.

## 2. Evidencia (campaña T42, ejecución `20261125-222227-ddffe96cb470`)

| Momento | Qué pasó | Efecto en la cola |
|---|---|---|
| 22:24, paso 5.2 | El equipo perdió la resolución de nombres (`getaddrinfo failed`, código 11001) | 8 jobs `FAILED` con `NETWORK` en unos segundos, uno por job, y uno `UNKNOWN` por un timeout (T42-D7). `run` siguió enviando jobs hasta vaciar la cola |
| 22:40 a 23:07, pasos 5.3 y 5.6 | La red ya funcionaba | Hizo falta `retry --all-failed` y otro `run` para recuperar los 9 jobs |
| 23:36, paso 5.7 | YouTube respondió `Sign in to confirm you're not a bot` a toda petición | Cada job falló en 1 o 2 s con `UNAVAILABLE`; su intento quedó gastado |
| 23:47 | El bloqueo seguía (cola `youtube-check`) | Los pasos 6 a 9, 11 y 13 de la campaña quedaron detenidos (`BLOCKED_BY_ENVIRONMENT`) |

Entre las 22:23 y las 23:36, los logs de las colas registran 93 extracciones de YouTube (81 videos y 12 playlists), más las 4 pruebas `network` de las suites. Eso está por debajo del límite de las sesiones de invitado que documenta yt-dlp (unos 300 videos por hora; página *Extractors* de la wiki de yt-dlp). El bloqueo no depende solo del número de peticiones, así que el ritmo reduce el riesgo pero no lo elimina.

## 3. Análisis de causa raíz

### 3.1 Bloqueo del sitio

- **Qué es.** YouTube marca la sesión de invitado o la dirección IP y deja de servir videos. yt-dlp 2026.11.23 (`extractor/youtube/_video.py`, en el tratamiento de `playabilityStatus`) distingue tres respuestas del sitio:
  - `Sign in to confirm you're not a bot`: comprobación antibots. yt-dlp añade la sugerencia de usar cookies.
  - Un `playerCaptchaViewModel`: el sitio pide un captcha.
  - `This content isn't available, try again later`: límite de peticiones. yt-dlp explica que la sesión queda limitada "hasta una hora" y recomienda el preajuste `-t sleep`.
- **Por qué el proyecto lo clasifica `UNAVAILABLE`.** yt-dlp lanza las tres con `raise_no_formats(reason, expected=True)`, un `ExtractorError` esperado sin clase propia. `failure_classifier` trata cualquier `ExtractorError` esperado como contenido no disponible (O-1 del [registro de la campaña](../project-management/t42-results.md)).
- **No es un problema de PO Token.** En yt-dlp 2026.11.23 los clientes por defecto son `tv_samsung` y `visionos` (`_DEFAULT_CLIENTS`), y ninguno exige PO Token (`GVS_PO_TOKEN_POLICY` en `extractor/youtube/_base.py`). El aviso de la wiki sobre PO Tokens afecta a otros clientes, como `mweb`. La restricción del §1 es compatible con la configuración actual. El riesgo es que YouTube extienda la exigencia a esos clientes; se vigila con el procedimiento de actualización de yt-dlp (SUP-S01) y el riesgo R-20.
- **Por qué la cola lo empeora:**
  - `run` envía el siguiente job en cuanto termina el anterior, sin pausa entre descargas del mismo sitio.
  - Tras un bloqueo, cada job falla en 1 o 2 s, así que la cola entera se marca `FAILED` en minutos.
  - Las peticiones siguen llegando al sitio mientras bloquea.
  - Cada fallo gasta un intento y obliga a un `retry` manual.

### 3.2 Corte de red

- **Qué es.** El equipo pierde la conexión: la resolución de nombres falla, la conexión es rechazada o no llega. El error llega como `RequestError` o `TransportError` dentro del `ExtractorError` o del `DownloadError`, y el proyecto lo clasifica `NETWORK`. Tras T42-D7, también cuando el downloader agota sus reintentos.
- **Por qué la cola lo empeora:** `run` no distingue entre "este job falló" y "el equipo está sin red". Sigue enviando jobs, que fallan uno tras otro.

## 4. Análisis de desperdicio

Se clasifican las actividades del User y del Evaluador ante estos dos sucesos: valor añadido (VA), necesaria para el negocio (BVA) o sin valor añadido (NVA). Los tipos de desperdicio siguen TIMWOODS.

| Actividad | Clase | Desperdicio | Observado en la campaña |
|---|---|---|---|
| Descargar un contenido | VA | — | — |
| Ver que la cola terminó con fallos y leer los motivos | NVA | Defectos: jobs sanos marcados `FAILED` | 5.2: 9 jobs; 5.7: todos los jobs desde las 23:36 |
| `retry --all-failed` y otro `run` | NVA | Sobreprocesamiento y defectos | 5.6 |
| Esperar a que vuelva la red o a que el sitio levante el bloqueo, vigilando la consola | NVA | Espera | Campaña detenida desde las 23:36 |
| Volver a comprobar a mano si el sitio ya responde | NVA | Movimiento | Colas `youtube-check` y `youtube-check-2` |
| Peticiones al sitio mientras bloquea | NVA (para el sitio y para el User) | Sobreprocesamiento; puede alargar el bloqueo | Jobs 1 y 2 de 5.7-r2, job 2 de 5.7-r3 |
| Repetir pasos de la campaña que no prueban YouTube (procesos, `Ctrl+C`, reanudación, propiedad de archivos) porque YouTube o la red fallaron | NVA | Espera y reprocesamiento | Pasos 6 a 9 y 11 dependen de descargas de YouTube |

Con los casos de uso nuevos, el producto quita las cinco primeras actividades NVA:

- **Ritmo:** el sitio bloquea menos.
- **Espera automática:** los jobs no se gastan y nadie tiene que vigilar ni reintentar.
- **Aviso con hora:** el User sabe qué espera y hasta cuándo.

La última actividad NVA es del proceso de validación. Se quita con un sitio de medios local para los pasos que prueban el sistema operativo y no YouTube (T57, §9).

## 5. Opciones evaluadas

| Opción | Evaluación | Decisión propuesta |
|---|---|---|
| Proveedor de PO Token (plugin) | Dependencia externa no afiliada a yt-dlp; tokens por video; contraria a la restricción del §1; no hace falta con los clientes por defecto (§3.1) | Descartada |
| Cookies o cuenta del sitio | La referencia (`yt-dlp-gui-kannagi`, `Wrappers/DLP.cs`) detecta el error con una expresión regular sobre `sign` y `confirm` y repite con `--cookies-from-browser` (modo `WhenNeeded` por defecto). La wiki de yt-dlp avisa del riesgo de que la cuenta sea bloqueada; [ADR-0004](../notes/adr-0004-windows-x64-target-platform.md) dejó pendiente verificar la lectura de cookies de Chrome en Windows | Fuera de alcance por ahora (decisión D-1) |
| Proxy | No resuelve la causa; añade configuración y una dependencia externa | Descartada |
| Ritmo de peticiones por sitio | yt-dlp recomienda `-t sleep`: `--sleep-interval 10 --max-sleep-interval 20 --sleep-requests 0.75` (`options.py`) | Adoptada (UC-11, SUP-P05) |
| Detectar el bloqueo y esperar por sitio, sin gastar los jobs | Quita los defectos y la vigilancia; deja de pedir al sitio mientras bloquea | Adoptada (UC-11) |
| Detectar el corte de red y esperar a que vuelva | Igual que la anterior, para la red | Adoptada (UC-12) |
| Reintento automático de un fallo de red aislado | Recupera timeouts sueltos sin intervención | Adoptada (UC-12 A1) |
| Sitio de medios local para la campaña | Los pasos que prueban procesos, cierres y archivos dejan de depender de YouTube y de la red | Adoptada (T57) |

## 6. Casos de uso afectados

| Caso de uso | Cambio |
|---|---|
| **UC-11 Esperar a que el sitio levante un bloqueo** (nuevo) | Ritmo de peticiones por sitio; detección del bloqueo; los jobs vuelven a `PENDING` sin gastar un intento; espera por sitio, persistente, con prueba al terminar y espera creciente |
| **UC-12 Esperar a que vuelva la red** (nuevo) | Detección del corte; los jobs vuelven a `PENDING`; comprobación periódica de la conexión; continuación automática; reintento automático de un fallo de red aislado |
| UC-01 Instalar y verificar el entorno | Nuevo A9: `diagnose` comprueba que resuelve el nombre de los sitios configurados, sin descargar nada |
| UC-03 Descargar un contenido | A2 deja de incluir los bloqueos del sitio y los cortes de red; A11 remite a UC-11 y A12 a UC-12; el paso 4 respeta el ritmo del sitio |
| UC-04 Expandir una playlist | A6 (fallo de red a mitad de la expansión) remite a UC-12; un bloqueo durante la expansión, a UC-11. Los hijos ya creados se conservan |
| UC-06 Recuperar la cola y reanudar descargas | Las esperas por sitio guardadas siguen vigentes tras un cierre; las de red no se guardan, porque la conexión se comprueba al arrancar |
| UC-08 Listar jobs, UC-09 Ver un job | Un job pendiente de un sitio en espera muestra el motivo y la hora estimada de continuación |
| UC-05, UC-07, UC-10 | Sin cambios: un job en espera es `PENDING`, y se cancela, no se reintenta ni se purga |

## 7. Requisitos no funcionales nuevos

Se añaden a la [especificación complementaria](supplementary-specification.md) como propuestos:

- **SUP-R06:** un corte de red no marca ningún job `FAILED`.
- **SUP-R07:** un bloqueo del sitio no marca ningún job `FAILED` ni gasta intentos.
- **SUP-P05:** ritmo de peticiones por defecto para YouTube.
- **SUP-U04:** toda espera se anuncia con su motivo y la hora estimada de continuación.

## 8. Decisiones del Responsable

| Id | Decisión | Recomendación |
|---|---|---|
| D-1 | ¿Cookies o cuenta del sitio? | Fuera de alcance en esta versión. Se reconsidera si el bloqueo antibots se vuelve habitual con el ritmo de SUP-P05 |
| D-2 | Cuando todos los jobs pendientes esperan a un sitio bloqueado, ¿`run` espera o termina? | Espera, con un aviso periódico; `Ctrl+C` lo detiene y los jobs siguen en la cola. Terminar obligaría al User a volver más tarde, que es el desperdicio que se quiere quitar |
| D-3 | Ritmo por defecto para YouTube | El de `-t sleep` (de 10 a 20 s entre descargas y 0,75 s entre peticiones), configurable hasta 0. Con 100 videos añade unos 25 minutos |
| D-4 | Espera ante un bloqueo | 60 minutos la primera vez (el plazo que indica yt-dlp), probar con un solo job y duplicar si sigue bloqueado, hasta 4 horas. Nunca `FAILED` por bloqueo |

## 9. Trabajo propuesto

| Tarea | Contenido | Depende de |
|---|---|---|
| T52 | Clasificar el bloqueo del sitio: motivo propio, detectado con el texto de yt-dlp y una prueba de contrato contra su código real (como `test_yt_dlp_download_retry_contract.py`); job event `JobDeferred`; transición `RUNNING → PENDING` sin gastar intento | — |
| T53 | Esperas por sitio persistentes (migración 0005), espera creciente y prueba con un job (UC-11) | T52 |
| T54 | Ritmo de peticiones por sitio en el proceso de `run` (no en el worker; ver ADR-0031) | T53 |
| T55 | Corte de red: detección, espera con comprobación periódica y reintento automático de un fallo aislado (UC-12) | T52 |
| T56 | `list`, `show` y `diagnose` (UC-08, UC-09, UC-01 A9) | T53, T55 |
| T57 | Sitio de medios local para la campaña: DASH con unión, archivo grande con velocidad limitada, playlist; el guion usa YouTube solo en los pasos que lo prueban (5.1 a 5.3 y la resolución de retos) | — |

## Fuentes

- Wiki de yt-dlp, *Extractors* (YouTube, PO Token, límite de peticiones) y *PO-Token-Guide*: texto entregado por el Responsable el 2026-11-26.
- yt-dlp 2026.11.23: `yt_dlp/extractor/youtube/_video.py` (`_DEFAULT_CLIENTS`, tratamiento de `playabilityStatus`), `yt_dlp/extractor/youtube/_base.py` (`GVS_PO_TOKEN_POLICY`, `_youtube_login_hint`), `yt_dlp/extractor/common.py` (`raise_no_formats`), `yt_dlp/options.py` (preajuste `sleep`), `yt_dlp/YoutubeDL.py` (`sleep_interval`, `max_sleep_interval`, `sleep_interval_requests`).
- Espacio de análisis, `upstream/source/yt-dlp-gui-kannagi`: `Wrappers/DLP.cs` (detección de `sign` y `confirm`, `--cookies-from-browser`) y `Views/Main.xaml.cs` (modos de cookies).
- IIBA, *BABOK Guide* v3: 10.34 Process Analysis y 10.40 Root Cause Analysis.
- [Registro de la campaña T42](../project-management/t42-results.md), ejecución `20261125-222227-ddffe96cb470`.
