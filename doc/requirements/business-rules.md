# Reglas de negocio

- **Fase RUP:** Elaboración
- **Versión:** 1.0 (propuesta; las reglas con decisión pendiente lo indican)
- **Fecha:** 2026-11-26
- **Técnica:** BABOK v3, 10.9 Business Rules Analysis
- **Origen:** [análisis del funcionamiento sin vigilancia](unattended-operation-analysis.md)

Las reglas se expresan de forma declarativa, una directiva por regla, separadas de los flujos que las usan y de cómo se implementan. Hay dos tipos:
- **Definicional (D):** define cómo se reconoce o se calcula algo.
- **De conducta (C):** obliga a algo o lo prohíbe.

Los valores son los valores por defecto propuestos; los configurables lo indican, junto con su clave. Cada caso de uso enlaza la regla desde el paso que la aplica.

| Id | Tipo | Regla | Usada en | Estado |
|---|---|---|---|---|
| BR-01 | D | Un **bloqueo del sitio** es una respuesta del sitio que rechaza la sesión o la IP, no el contenido. Con yt-dlp 2026.11.23 son tres respuestas de YouTube: `Sign in to confirm you're not a bot`, la petición de un captcha y `This content isn't available, try again later`. Un contenido que pide una cuenta por sí mismo (privado, con restricción de edad, solo para miembros) **no** es un bloqueo del sitio | UC-11, UC-03 A2 | Propuesta |
| BR-02 | C | Entre el inicio de dos jobs del mismo sitio pasa una pausa aleatoria entre `site_request_interval_seconds` y `site_request_max_interval_seconds`. Dentro de una extracción, entre petición y petición, pasan `site_sleep_requests_seconds`. Para YouTube: de 10 a 20 s y 0,75 s (preajuste `-t sleep` de yt-dlp). Para los demás sitios: 0 | UC-11 | Decisión D-3 |
| BR-03 | C | Tras un bloqueo, el sistema no envía jobs a ese sitio durante una espera de `site_block_wait_minutes` (60). Al terminar, envía un solo job. Si el bloqueo sigue, la siguiente espera dura el doble, hasta `site_block_max_wait_minutes` (240) | UC-11 | Decisión D-4 |
| BR-04 | C | Un job **aplazado** (por un bloqueo del sitio, un corte de red o un disco lleno) vuelve a `PENDING` sin incrementar `attempt_count`, y conserva sus archivos parciales y la reclamación de su nombre final. Un aplazamiento nunca deja un job `FAILED` | UC-11, UC-12, UC-13 | Propuesta |
| BR-05 | D | Hay un **corte de red** cuando un job falla porque no se resuelve el nombre del host, la conexión es rechazada o la red no es alcanzable. También cuando dos jobs distintos fallan con `NETWORK` en menos de `network_check_seconds` | UC-12 | Propuesta |
| BR-06 | D | **Hay conexión** cuando el sistema resuelve el nombre del último host que falló y abre una conexión TCP a su puerto 443. La comprobación no hace peticiones HTTP al sitio | UC-12 | Propuesta |
| BR-07 | C | Un **fallo de red aislado** (hay conexión según BR-06) se reintenta en el mismo job hasta `network_retry_attempts` veces (2): tras `network_retry_delay_seconds` (10 s) y luego el doble. Después, el job pasa a `FAILED` con `NETWORK` | UC-12 | Propuesta |
| BR-08 | D | Hay **disco lleno** cuando una escritura falla por falta de espacio (`ENOSPC`, o los errores 112 o 39 de Windows), también si es ffmpeg el que no puede escribir. También cuando, antes de enviar un job, el espacio libre de la unidad de las descargas o de la del estado es menor que `min_free_disk_mib` (1024) | UC-13 | Decisión D-5 |
| BR-09 | C | Mientras hay disco lleno, el sistema no envía jobs y comprueba el espacio libre cada `disk_check_seconds` (60). Continúa cuando las dos unidades superan `min_free_disk_mib` | UC-13 | Propuesta |
| BR-10 | C | Con la cola **en pausa**, el sistema no envía jobs y deja terminar los que están en curso. Con `pause --now`, los detiene como un `Ctrl+C`: siguen `RUNNING` con sus parciales y se reanudan al continuar | UC-14 | Decisión D-6 |
| BR-11 | C | Toda espera de `run` se anuncia con su motivo y la hora local estimada de continuación, si la hay. El aviso se repite mientras dura: cada `site_block_notice_minutes` (15) en las esperas de un sitio y cada `network_notice_minutes` (5) en las demás | UC-11 a UC-14 | Propuesta (SUP-U04) |
| BR-12 | C | El sistema nunca usa PO Tokens, cookies ni cuentas de los sitios | UC-11 | PO Tokens: decisión del Responsable (2026-11-26). Cookies y cuentas: decisión D-1 |

## Reglas de la validación

| Id | Tipo | Regla | Usada en |
|---|---|---|---|
| VBR-01 | C | Un bloque de la campaña que no prueba el comportamiento de un sitio real usa los medios locales (VUC-05) | VUC-04 |
| VBR-02 | D | Un bloque **pasa** cuando todas sus comprobaciones pasan. **Falla** cuando alguna falla por el producto. Queda **bloqueado por el entorno** cuando la comprobación previa del sitio (VUC-06) falla o un suceso externo detectado (BR-01, BR-05) impide completarlo | VUC-04, VUC-08 |
| VBR-03 | C | Ningún bloque continúa después de que su comprobación previa del sitio detecte un bloqueo: no se suman peticiones a un sitio que bloquea | VUC-06 |
