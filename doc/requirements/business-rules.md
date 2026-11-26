# Reglas de negocio

- **Fase RUP:** Elaboración
- **Versión:** 2.0 (2026-11-26). Las reglas vigentes describen el código de `main`; las propuestas indican la decisión de la que dependen.
- **Técnica (BABOK v3):** 10.9 Business Rules Analysis
- **Origen:** [análisis de requisitos](requirements-analysis.md) y casos de uso vigentes

Una regla es una directiva declarativa, con una sola autoridad: este catálogo. Los casos de uso la enlazan desde el paso que la aplica, y el código la implementa en un solo lugar. Hay dos tipos:
- **Definicional (D):** define cómo se reconoce o se calcula algo.
- **De conducta (C):** obliga a algo o lo prohíbe.

Las reglas no contienen valores numéricos. Los valores son **parámetros** (§3), con su clave de configuración, su evidencia y su estado; un valor sin evidencia figura como pendiente y no se presenta como regla. Las decisiones están en el [análisis, §9](requirements-analysis.md#9-decisiones-pendientes); las restricciones, en la [especificación complementaria](supplementary-specification.md); los criterios de aceptación, en cada caso de uso.

## 1. Reglas vigentes

Implementadas y verificadas por las pruebas automáticas de `main`.

| Id | Tipo | Regla | Usada en |
|---|---|---|---|
| BR-13 | C | Un job `DOWNLOAD` cuya media key ya tiene otro job `DOWNLOAD` activo queda `SKIPPED` como **duplicado**. La comparación se hace al conocer la media key (al extraer o al expandir), no al encolar; un job terminado no cuenta como activo | UC-03 A1, UC-04 A2; SUP-R05 |
| BR-14 | D | Un job es **reintentable** si está `FAILED` o `CANCELLED`, y **cancelable** si está `PENDING` o `RUNNING` ([vocabulario, §1.1](../design/00-vocabulary.md#11-estados-terminados-reintentables-y-cancelables)) | UC-05, UC-07 |
| BR-15 | C | Cada reintento pedido por el User incrementa `attempt_count`; la recuperación de un job interrumpido no lo incrementa | UC-06, UC-07 |
| BR-16 | C | Cancelar una playlist expandida cancela sus entradas no terminadas (T42-D10) | UC-05 A4 |
| BR-17 | C | Un job solo escribe un nombre final que haya reclamado con su owner token; nunca sobrescribe, mueve ni borra un archivo que no escribió ([ADR-0030](../notes/adr-0030-final-file-ownership-claims.md)) | UC-03 A7, UC-06 A7 y A8 |
| BR-18 | C | Purgar borra registros de la cola, nunca archivos descargados | UC-10 |
| BR-19 | C | Al arrancar, `run` devuelve a la cola los jobs `RUNNING` de una ejecución anterior, sin gastar intentos, y continúan desde sus parciales | UC-06; SUP-R01 |
| BR-20 | C | Una entrada de playlist que el sitio marca no disponible en la propia lista se crea `SKIPPED` | UC-04 A3 |
| BR-21 | C | Si el formato guardado ya no está disponible al reanudar, el job se reintenta una sola vez con el format selector original | UC-06 A1 |
| BR-22 | C | El motivo de un fallo es el que asigna el clasificador a partir de la causa más interna de la excepción ([catálogo de condiciones de fallo](failure-conditions.md)) | UC-03 A2 |

## 2. Reglas propuestas

Ninguna está implementada. Las que dependen de una decisión pendiente lo indican.

| Id | Tipo | Regla | Usada en | Estado |
|---|---|---|---|---|
| BR-01 | D | Una **restricción del sitio** es una respuesta que rechaza la sesión o la IP, no el contenido. Con yt-dlp 2026.11.23 son: `Sign in to confirm you're not a bot`, la petición de un captcha, `This content isn't available, try again later` y HTTP 429. Un contenido que pide una cuenta por sí mismo (privado, con restricción de edad, solo para miembros) **no** es una restricción del sitio | UC-11 A1, UC-03 A2, UC-15 E3 | Propuesta |
| BR-02 | C | Entre el inicio de dos jobs del mismo sitio pasa una pausa aleatoria acotada, y dentro de una extracción, una pausa entre peticiones (parámetros `site_request_*` y `site_sleep_requests_seconds`) | UC-11 A1, UC-15 | Decisión D-3 |
| BR-03 | C | Mientras dura una restricción de un sitio, el sistema no le envía jobs. Si la política de continuidad (D-2) espera, al terminar el plazo envía un solo job de prueba, y si la restricción sigue, el plazo crece hasta un máximo (parámetros `site_block_*`) | UC-11 | Decisiones D-2 y D-4 |
| BR-04 | C | Un job **aplazado** por una condición externa vuelve a `PENDING` sin incrementar `attempt_count` y conserva sus parciales y su reclamación. Un aplazamiento nunca deja un job `FAILED` | UC-11 | Propuesta |
| BR-05 | D | Hay un **corte de conectividad** cuando un job falla porque no se resuelve el nombre del host, la conexión es rechazada o la red no es alcanzable, en cualquier punto de la cadena de causas | UC-11 A2 | Propuesta |
| BR-06 | D | **Hay conexión** cuando el sistema resuelve el nombre del último host que falló y abre una conexión TCP a su puerto. La comprobación nunca hace peticiones HTTP al sitio | UC-11 A2 | Propuesta |
| BR-07 | C | Los reintentos ante fallos transitorios de una descarga (HTTP 5xx, timeouts, conexiones cortadas) se delegan en yt-dlp, con los mismos valores que yt-dlp usa por defecto en su línea de comandos (parámetros `retries` y `fragment_retries`). La cola no añade un reintento propio por encima | UC-03, UC-11 paso 1 | Propuesta; corrige la divergencia R-24 |
| BR-08 | D | Hay **almacenamiento insuficiente** cuando una escritura falla por falta de espacio (`ENOSPC`, `EDQUOT`, `winerror` 112 o 39, o el mensaje equivalente de ffmpeg) en cualquier punto de la cadena de causas, o cuando, antes de enviar un job, el espacio libre de la unidad de las descargas o de la del estado es menor que un mínimo (`min_free_disk_mib`) | UC-11 A3 | Decisión D-5 |
| BR-09 | C | Mientras hay almacenamiento insuficiente en una unidad, el sistema no envía los jobs que escriben en ella. Continúa cuando el espacio supera el mínimo de BR-08 | UC-11 A3 | Decisiones D-2 y D-5 |
| BR-10 | C | Con la cola **en pausa**, el sistema no envía jobs y deja terminar los que están en curso. Con una pausa inmediata, los detiene como una interrupción: siguen `RUNNING` con sus parciales y se reanudan al continuar | UC-14 | Decisión D-6 |
| BR-11 | C | Toda espera o pausa de `run` se anuncia con su motivo, su alcance y, si la hay, la hora local estimada de continuación. El aviso se repite mientras dura | UC-11, UC-14 | Propuesta (SUP-U04) |
| BR-12 | C | El sistema nunca usa PO Tokens ni mecanismos para evadir los controles de un sitio. Las cookies y el proxy solo se aceptan como acceso legítimo configurado por el User | UC-11, UC-01 A11 | PO Tokens: decisión del Responsable (2026-11-26). Cookies: D-1. Proxy: D-7 |
| BR-23 | C | Un job interrumpido solo se completa sin consultar al sitio si hay evidencia local suficiente: su reclamación con su owner token, un archivo final con el nombre reclamado y la confirmación de que ese archivo es legible y completo. Un archivo no vacío no basta | UC-06 A11 | Decisión D-9 |
| BR-24 | C | Una transmisión en directo o programada no ocupa un worker sin límite | UC-03 E (directos) | Decisión D-10 |

## 3. Parámetros

Valores configurables que usan las reglas. Un valor sin evidencia queda **pendiente**: se fija al implementar la regla, con su evidencia.

| Clave | Regla | Valor propuesto | Evidencia | Estado |
|---|---|---|---|---|
| `site_request_interval_seconds`, `site_request_max_interval_seconds` | BR-02 | YouTube: 10 y 20 s; otros sitios: 0 | Preajuste `-t sleep` de yt-dlp 2026.11.23 (`--sleep-interval 10 --max-sleep-interval 20`) | Decisión D-3 |
| `site_sleep_requests_seconds` | BR-02 | YouTube: 0,75 s | El mismo preajuste (`--sleep-requests 0.75`) | Decisión D-3 |
| `site_block_wait_minutes`, `site_block_max_wait_minutes` | BR-03 | Pendiente | yt-dlp dice que la restricción dura "hasta una hora", sin más precisión. Ninguna referencia espera un plazo largo: Seal y VoiceStudio fallan el job; Kannagi no lo distingue | **Pendiente**, sin evidencia |
| `retries`, `fragment_retries` | BR-07 | 10 y 10 | Valores por defecto de la línea de comandos de yt-dlp (`options.py`); la librería usa 0 | Propuesta |
| `extractor_retries` | BR-07 | 3 | Valor por defecto de la librería, ya efectivo | Vigente (sin cambio) |
| `socket_timeout` | BR-07 | 20 s | `DEFAULT_TIMEOUT` de yt-dlp, ya efectivo | Vigente (sin cambio) |
| `file_access_retries` | — | 10 | Ya lo pasa `build_yt_dlp_parameters` | Vigente |
| `min_free_disk_mib` | BR-08 | Pendiente | Depende del tamaño típico de un job y del espacio que necesita ffmpeg para unir (hasta 2 veces el contenido); sin medición | **Pendiente**, sin evidencia |
| `disk_check_seconds`, `network_check_seconds` | BR-06, BR-09 | Pendiente | Sin evidencia | **Pendiente** |
| `site_block_notice_minutes`, `network_notice_minutes` | BR-11 | Pendiente | Sin evidencia; el aviso de cola ocupada de T42-D12 se repite cada 30 s | **Pendiente** |
| `rate_limit` | SUP-P06 | Sin límite | Seal, Kannagi y yt-dlp lo ofrecen sin valor por defecto | Propuesta |

## 4. Reglas retiradas

| Id | Motivo |
|---|---|
| BR-07 (versión 1.0) | Proponía un reintento propio de la cola (2 intentos, 10 s y el doble). Se sustituye por la delegación en yt-dlp: el reintento propio duplicaba un mecanismo que yt-dlp ya tiene y que hoy está desactivado por omisión (R-24) |

## Reglas de la validación

| Id | Tipo | Regla | Usada en |
|---|---|---|---|
| VBR-01 | C | Un bloque de la campaña que no prueba el comportamiento de un sitio real usa los medios locales (VUC-05) | VUC-04 |
| VBR-02 | D | Un bloque **pasa** cuando todas sus comprobaciones pasan. **Falla** cuando alguna falla por el producto. Queda **bloqueado por el entorno** cuando la comprobación previa del sitio (VUC-06) falla o un suceso externo detectado (BR-01, BR-05) impide completarlo | VUC-04, VUC-08 |
| VBR-03 | C | Ningún bloque continúa después de que su comprobación previa del sitio detecte una restricción: no se suman peticiones a un sitio que restringe | VUC-06 |
| VBR-04 | C | Quien ejecuta una prueba no decide si pasó: el veredicto lo emite una comprobación automática independiente sobre la evidencia guardada | VUC-03, VUC-07 |
