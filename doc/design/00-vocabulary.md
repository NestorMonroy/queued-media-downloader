# Diseño — Parte 0: vocabulario del proyecto

- **Estado:** Borrador para revisión
- **Fecha:** 2026-11-22; términos de producto, interfaz, contrato público y capacidades añadidos el 2026-11-26 (instrucción 2.3.0)
- **Base:** [principios de nombres](../reference/naming-principles/clean-code-naming-principles.md) y [guías de clean code](../reference/clean-code-guidelines/practise/naming.md)

Este documento fija **una palabra por concepto** (principio #8). Todo identificador del código y todo término del diseño debe salir de aquí. Si hace falta un concepto nuevo, se añade aquí antes de usarlo.

---

## 1. Conceptos del dominio

| Palabra | Significa | No usar |
|---|---|---|
| **job** | Unidad de trabajo de la cola: expandir una URL o descargar un contenido | task, item, entry (como sinónimo de job) |
| **job kind** | Tipo de job: `EXPANSION` o `DOWNLOAD` | type, mode |
| **job status** | Estado del ciclo de vida de un job | state, phase |
| **expansion** | Resolver una URL para descubrir qué contenidos contiene | resolve, flatten, unpack |
| **playlist** | Colección de contenidos que produce varios jobs hijos | list, collection |
| **playlist entry** | Elemento descubierto al expandir una playlist, antes de ser job | item, child (antes de crearse el job) |
| **media** | Contenido descargable (video o audio) | video (salvo que sea solo video), file |
| **media key** | Identidad de un contenido: extractor + identificador | id (a secas), archive id |
| **download options** | Opciones con las que se descarga un contenido | options (a secas), settings, config |
| **format selector** | Expresión de yt-dlp que elige formatos (`bv*+ba/b`) | format (a secas), quality |
| **selected format** | Formato concreto que yt-dlp eligió para un job | chosen format, format code |
| **failure reason** | Clasificación de dominio de un fallo | error type, error code |
| **output claim** (reclamación) | Archivo exclusivo en `state/output-claims/` con el que un job se declara dueño de un nombre final antes de descargar ([ADR-0030](../notes/adr-0030-final-file-ownership-claims.md)) | lock (no es un bloqueo del sistema operativo), reservation |
| **owner token** | Identidad de un job en los archivos que reclama: su id y el instante en que se guardó (`Job.owner_token`, `<id>@<created_at>`). Distingue a dos jobs con el mismo id tras restaurar una copia antigua de la base de datos | job id (a secas, para la propiedad) |
| **site key** (sitio) | Sitio al que pertenece un job: el extractor de yt-dlp que acepta su URL o, si no hay ninguno, su host. Se fija al encolar ([ADR-0031](../notes/adr-0031-site-waits-and-network-waits.md), propuesta) | domain, host (salvo que sea el host) |
| **site block** (bloqueo del sitio) | El sitio deja de servir contenidos a la sesión o a la IP: comprobación antibots, captcha o límite de peticiones. No es un fallo del job ([UC-11](../requirements/use-cases/uc-11-preserve-jobs-under-external-conditions.md) A1, [BR-01](../requirements/business-rules.md)); en los requisitos, «restricción del sitio» | ban, rate limit (a secas), unavailable |
| **network outage** (corte de red) | El equipo no tiene conexión: no resuelve nombres o no llega a ningún host ([UC-11](../requirements/use-cases/uc-11-preserve-jobs-under-external-conditions.md) A2, [BR-05](../requirements/business-rules.md)); en los requisitos, «corte de conectividad» | offline error, network failure (para un fallo aislado) |
| **defer** (aplazar) | Devolver un job a `PENDING` sin gastar un intento, por una condición externa (`JobDeferred`, [BR-04](../requirements/business-rules.md)) | retry (es una petición del User), postpone, requeue |
| **insufficient storage** (almacenamiento insuficiente) | No hay espacio, o se excedió la cuota, para escribir en una unidad de destino o de estado ([UC-17](../requirements/use-cases/uc-17-preserve-work-under-storage-failures.md), [BR-08](../requirements/business-rules.md)). No incluye el acceso denegado ni el uso compartido | disk full (a secas, para la cuota), out of space (como error del job) |
| **sharing violation** (conflicto de uso compartido) | Otro proceso retiene un archivo (`winerror` 32 o 33); suele ser transitorio ([BR-26](../requirements/business-rules.md)) | locked (a secas), access denied |
| **cause chain** (cadena de causas) | Excepciones enlazadas por `DownloadError.exc_info`, `__cause__` y `__context__`; la condición se identifica en toda la cadena ([BR-25](../requirements/business-rules.md)) | inner error (a secas) |
| **job output** (resultado) | Cada archivo o elemento que un job produce por su petición, con su tipo (multimedia principal, multimedia adicional, complementario) y su obligatoriedad ([BR-29](../requirements/business-rules.md)). En el código, `JobOutput` (ADR-0033): «result» ya designa el resultado de una operación (`CancelJobResult`, `RunQueueResult`); se respeta una palabra por concepto | job result (en código), artifact |
| **required output** / **optional output** (resultado obligatorio u opcional) | Si su ausencia impide completar el job o solo deja un aviso ([BR-30](../requirements/business-rules.md)) | mandatory file |
| **supplementary information** (información complementaria) | Subtítulos, descripción, metadatos, miniatura, capítulos e `info.json` que publica el sitio ([UC-24](../requirements/use-cases/uc-24-retrieve-supplementary-media-information.md)); nunca generada con IA | extras, sidecar (a secas) |
| **variant** (variante) | Otra petición del mismo contenido con otra especificación de resultado ([BR-32](../requirements/business-rules.md)) | duplicate (si la especificación difiere) |
| **download profile** (perfil de descarga) | Conjunto con nombre de download options validadas que se copia en el job al encolar ([UC-18](../requirements/use-cases/uc-18-manage-download-profiles.md), BR-33) | preset (a secas), template, config |
| **access profile** (perfil de acceso) | Referencia con nombre a credenciales legítimas del User para ciertos sitios; nunca contiene el secreto ([UC-19](../requirements/use-cases/uc-19-manage-authorized-access-profiles.md), BR-34) | account, login, cookie profile |
| **execution window** (ventana de ejecución) | Intervalo programado en el que `run` puede enviar jobs ([UC-21](../requirements/use-cases/uc-21-schedule-queue-execution.md), BR-37) | schedule (a secas, para la ventana), cron |
| **program client** (programa cliente) | Otro programa que usa el producto sin interpretar texto para personas (SUP-I01); es un *consumer* | bot, agent (a secas), consumidor programático |
| **media identity** (identidad del contenido) | El contenido remoto: `MediaKey` (extractor + id) | content id |
| **request identity** (identidad de la petición) | El resultado pedido: media key + especificación normalizada del resultado, con la versión del algoritmo ([BR-32](../requirements/business-rules.md), D-16). No incluye opciones operativas ni el acceso | request hash, fingerprint |
| **job identity** (identidad del job) | El trabajo persistido: `job_id` + `created_at`, el **owner token** | id (a secas) |
| **output identity** (identidad del resultado) | La identidad del job más la clave del output (tipo y discriminante: `video`, `subtitle:es`). No incluye la ruta ([ADR-0033](../notes/adr-0033-output-identity-and-storage-references.md)) | result identity (en código), path (como identidad) |
| **ownership evidence** (evidencia de propiedad) | Reclamación con el owner token y registro del resultado; no prueba la integridad ([BR-31](../requirements/business-rules.md)) | lock |
| **output** | Término del código para un resultado (`output_path`, output claim, `JobOutput`). En los requisitos, «resultado» | result (para un archivo) |
| **effective configuration** (configuración efectiva) | Valores que resultan de la precedencia argumentos > variables de entorno > `config.toml` > valores por defecto, con el perfil para las opciones de resultado (§13.17 del análisis) | settings (a secas) |
| **verification** (verificación) | Comprobar la conformidad con un contrato: pruebas automáticas o UC-26 sobre un resultado | validation |
| **validation** (validación) | Demostrar que el producto sirve a su propósito en la plataforma objetivo (campaña en Windows) | verification |
| **backup** / **restore** (respaldo, restauración) | Copia coherente del estado de una instalación y su recuperación en ella (UC-23) | export (no traslada) |
| **export** / **import** (exportar, importar) | Traslado versionado de jobs, historial y preferencias a otra instalación, sin propiedad ni secretos (UC-22) | backup (no restaura) |
| **cancel** frente a **pause**, **stop** e **interruption** | Cancelar: el User ya no quiere el job. Pausar: dejar de enviar jobs, conservando la intención. Detener: terminar `run` de forma ordenada. Interrumpir: `Ctrl+C`, sin intención persistida (D-6) | — |
| **pause** (pausa) | Estado de la cola en el que `run` no envía jobs; no cambia el estado de ningún job ([UC-14](../requirements/use-cases/uc-14-control-queue-execution.md)) | suspend, stop, hold |
| **business rule** (regla de negocio) | Directiva declarativa que gobierna una decisión de un caso de uso, en el [catálogo](../requirements/business-rules.md) | policy (a secas), setting |
| **site wait** (espera del sitio) | Plazo durante el que `run` no envía jobs de un sitio bloqueado; se guarda en la base de datos | cooldown, ban, pause (a secas) |
| **request pacing** (ritmo de peticiones) | Pausa entre jobs del mismo sitio para no llegar a su límite | throttling, rate limit (a secas) |
| **interruption** (interrupción) | `Ctrl+C` durante `run`: detiene la cola sin cancelar ningún job; los jobs en curso conservan su estado y sus parciales y continúan en el siguiente `run` | cancel (no es una cancelación) |
| **external condition** (condición externa) | Suceso ajeno al contenido que impide descargar: restricción del sitio, corte de conectividad o almacenamiento insuficiente ([UC-11](../requirements/use-cases/uc-11-preserve-jobs-under-external-conditions.md), [catálogo de condiciones de fallo](../requirements/failure-conditions.md)) | environment error, transient error (a secas) |

### 1.0 Conceptos de continuidad

Conceptos distintos que a menudo se confunden. Cada uno tiene un responsable: yt-dlp (dentro de un job) o la cola (entre jobs). Fuente: [análisis de requisitos, §7](../requirements/requirements-analysis.md#7-continuidad-reintentos-y-recuperación).

| Palabra | Significa | Responsable | Estado |
|---|---|---|---|
| **retry** (reintento automático) | Repetir una petición o un fragmento tras un fallo transitorio, dentro del mismo job | yt-dlp (`retries`, `fragment_retries`, `extractor_retries`, `file_access_retries`) | Parcial: solo los de extractor y de acceso a archivos están activos (R-24) |
| **job retry** (reintento del job) | Volver a poner en la cola un job `FAILED` o `CANCELLED` a petición del User (UC-07) | Cola | Vigente |
| **backoff** (espera creciente) | Aumentar la espera entre reintentos sucesivos | yt-dlp dentro de un job (`retry_sleep_functions`); la cola, entre comprobaciones de una restricción (BR-03) | yt-dlp: sin configurar; cola: propuesto |
| **request pacing** (ritmo de peticiones) | Ver §1; previene una restricción, no reacciona a ella | yt-dlp dentro de una extracción (`sleep_interval_requests`); la cola entre jobs (BR-02) | Propuesto |
| **rate limit** (límite de ancho de banda) | Tope de bytes por segundo de una descarga (SUP-P06). No es el límite de peticiones de un sitio | yt-dlp (`ratelimit`) | Propuesto |
| **deferred execution** (ejecución aplazada) | Un job aplazado espera a que desaparezca una condición externa (BR-04) | Cola | Propuesto |
| **admission control** (control de admisión) | Decidir antes de enviar un job si puede avanzar: sitio restringido, sin conexión, sin espacio, cola en pausa | Cola | Propuesto |
| **pause** / **resume** | Ver §1; la cola deja de enviar jobs y vuelve a enviarlos (UC-14) | Cola | Propuesto |
| **stop** (detención ordenada) | `run` termina al acabar los jobs en curso, sin cancelar ninguno (UC-14 A2) | Cola | Propuesto |
| **recovery** (recuperación) | Al arrancar, devolver a la cola los jobs `RUNNING` de una ejecución anterior (UC-06, BR-19) | Cola | Vigente |
| **resume** de una descarga | Continuar desde el `.part` o el `.ytdl` (`continuedl`) | yt-dlp | Vigente |

### 1.1 Estados terminados, reintentables y cancelables

Tres preguntas distintas sobre un job status, con respuestas distintas (`Job.is_finished`, `Job.can_be_retried`, `CancelJob`):

| Job status | Terminado | Reintentable (`retry`) | Cancelable (`cancel`) | Purgable sin opciones (`purge`) |
|---|---|---|---|---|
| `PENDING` | No | No | Sí: pasa a `CANCELLED` (UC-05 A1) | No |
| `RUNNING` | No | No | Sí: `CANCELLATION_REQUESTED` (UC-05) | No |
| `CANCELLATION_REQUESTED` | No | No | Sin cambios (ya se está cancelando) | No |
| `COMPLETED` | Sí | No | Sin cambios (A7) | Sí |
| `FAILED` | Sí | **Sí** | Sin cambios (A7): conserva su failure reason; se reintenta, no se cancela | No |
| `CANCELLED` | Sí | **Sí** | Sin cambios (A7) | Sí |
| `SKIPPED` | Sí | No | Sin cambios (A7) | Solo con su playlist; un `SKIPPED` suelto (UC-03 A1) no se purga (restricción de UC-10) |

Una playlist (`EXPANSION`) se purga solo si todas sus entradas son purgables con las opciones elegidas o son `SKIPPED`; si no, se conserva con sus entradas pendientes de trabajo (UC-10 A2).

## 2. Conceptos de ejecución

| Palabra | Significa | No usar |
|---|---|---|
| **worker** | Proceso (o hilo, en el prototipo) que ejecuta jobs | executor, runner, slave |
| **worker pool** | Conjunto fijo de workers | executor pool, cluster |
| **job event** | Hecho que le ocurrió a un job; lo publica un worker hacia el proceso principal | worker event, notification, callback, signal |
| **worker instruction** | Mensaje del proceso principal hacia un worker (`RunJob`, `CancelJob`, `ShutDown`) | command, task, order |
| **job request** | Petición de un usuario sobre un job existente (`CANCEL`, `RETRY`), guardada para el proceso de la cola | command, action |
| **cancel** | Intención sobre un **job**: que deje de ejecutarse | abort, stop, kill (para jobs) |
| **terminate** | Acción sobre **procesos** del sistema operativo | kill, cancel (para procesos) |
| **process tree** | Un worker y todos los procesos que crea (ffmpeg, deno) | process group, job object (en nombres propios) |
| **publish** | Enviar un job event | emit, send, notify |
| **recover** | Corregir jobs interrumpidos por un cierre inesperado | resume (reservado para continuar una descarga) |
| **resume** | Continuar una descarga parcial desde los archivos `.part` | recover, restart |

## 3. Conceptos de estructura

| Palabra | Significa | No usar |
|---|---|---|
| **component** | Paquete que representa una parte del dominio (`jobs`, `job_queue`, `workers`…), con su contrato y sus implementaciones | module (para un paquete), layer |
| **contract** | Interfaz (`Protocol`) que un componente expone a los demás; el archivo se llama como el contrato (`job_store.py`) | port, interface (en nombres), common |
| **implementation** | Clase que cumple un contrato (`SqliteJobStore`); es interna de su componente y solo la importa `command_line/composition_root.py` | adapter, impl |
| **public API** | Lo que exporta el `__init__.py` de un componente: contratos y tipos. Es lo único que otros componentes pueden importar | facade, exports |
| **product** (producto) | `queued-media-downloader`: sus reglas, contratos y capacidades, independientes de la interfaz ([ADR-0032](../notes/adr-0032-reusable-engine-and-platform-capabilities.md)) | app (para el producto) |
| **application** (aplicación) | Un programa distribuible para una plataforma que ofrece el producto: la CLI de Windows y, en el futuro, la GUI de Windows y las aplicaciones de Android e iOS | product |
| **interface** (interfaz) | La forma de interacción de una aplicación con el User (línea de comandos, ventana, pantalla táctil) | UI layer, frontend (a secas) |
| **consumer** (consumidor) | Toda interfaz o programa cliente que usa los contratos públicos | client (a secas) |
| **functional contract** (contrato funcional) | Lo que promete una operación según los casos de uso y las business rules, sea cual sea el transporte | — |
| **public contract** (contrato público) | La representación versionada del contrato funcional para los consumidores: operaciones, vistas, eventos, errores, progreso y capacidades. No confundir con *contract* (Protocol entre componentes) | API (a secas) |
| **view** (vista) | Representación pública de una entidad para una consulta, distinta de la entidad interna (`JobView`, nombre candidato) | DTO |
| **installation** (instalación) | Una carpeta de estado con su cola, sus reclamaciones, su configuración y su log, en un ambiente | workspace, profile (para esto) |
| **run session** (sesión de ejecución) | Abrir una instalación, recuperar los jobs interrumpidos y ejecutar la cola hasta terminar o detenerse | run loop |
| **execution environment** (ambiente de ejecución) | Sistema operativo, runtime y permisos donde se ejecuta una aplicación | platform (cuando se habla de permisos o runtime) |
| **platform capability** (capacidad del ambiente) | Una responsabilidad cuya implementación varía por ambiente (ejecución, almacenamiento, secretos, programación, avisos, multimedia), con su propio contrato | platform adapter |
| **storage reference** (referencia de almacenamiento) | Cómo se llega a un output en un ambiente: una ruta en Windows; un URI o un bookmark en móvil. No es identidad | path (como identidad) |
| **media source** (`MediaSource`) | Contrato que extrae y descarga un contenido; su implementación usa yt-dlp. El origen remoto es el *site* | downloader (para el contrato) |
| **request** (petición) | Lo que el User pide obtener: URL, preferencias de resultado y clase de contexto de acceso. Distinto de *job request* (instrucción a una cola en ejecución) | order |
| **access context class** (clase de contexto de acceso) | Identificador opaco del perfil de acceso, o anónimo, que forma parte de la identidad de la petición; nunca las credenciales | session (para esto) |
| **execution policy** (política de ejecución) | Las reglas que aplica la *admission control*: ventanas, pausa, límites, aplazamientos | scheduler (para la política) |
| **runtime** | Intérprete que ejecuta código: el de Python que ejecuta el producto, o el de JavaScript (deno) que usa yt-dlp para los retos de YouTube | engine (para el intérprete) |
| **notification** (aviso) | Entrega de un suceso operativo por un canal del ambiente; nunca es autoridad del estado (D-14) | alert, toast (en nombres) |
| **composition root** | Módulo de un programa que crea las implementaciones y las conecta (`command_line/composition_root.py`) | bootstrap, container, wiring |

## 4. Conceptos del proceso

| Palabra | Significa | No usar |
|---|---|---|
| **phase** (fase) | Fase de RUP: Inicio, Elaboración, Construcción, Transición | stage, etapa |
| **iteration** (iteración) | Periodo que termina en software ejecutable y una evaluación (E1, E2…) | sprint, cycle |
| **slice** | Incremento vertical ejecutable de extremo a extremo que implementa un escenario de un caso de uso a través de los componentes | rebanada, feature, increment |
| **task** (tarea) | Unidad de trabajo del proyecto dentro de un slice (`T01`…), con una prueba como criterio de terminado | ticket, story; nunca como sinónimo de *job* |

| **project lead** (Responsable del proyecto) | Rol que decide alcance, acepta ADR e integra en `main` | nombres de personas |
| **implementation agent** (Agente de implementación) | Rol que redacta artefactos y escribe pruebas y código | nombres de productos o modelos de IA |
| **Windows evaluator** (Evaluador en Windows) | Rol que ejecuta las pruebas `windows` y las verificaciones manuales | tester (a secas) |

*Task* es un concepto del proceso y *job* uno del dominio: un job es trabajo de la cola de descargas; una tarea es trabajo del equipo que desarrolla.

## 5. Verbos de acceso a datos

Siguiendo la guía de verbos por concepto (`create`, `get`, `update`):

| Verbo | Uso | No usar |
|---|---|---|
| `create` | Guardar algo nuevo | add, insert, save (para nuevo) |
| `get` | Leer sin modificar | fetch, retrieve, find, load |
| `update` | Modificar algo existente | save, edit, modify, set |
| `delete` | Eliminar | remove, purge (en código; `purge` sí como comando de la CLI) |
| `has_` / `is_` | Consultas booleanas, siempre en positivo | `not_exists`, `is_missing` |

## 6. Reglas de forma

- **Sin codificaciones** (#6): nada de prefijos `ix_`, `ux_`, `I` en interfaces, ni sufijos de tipo como `_json`, `_list`, `_dict`.
- **Sin palabras de ruido** (#3): `data`, `info`, `manager`, `helper`, `util`, `stuff`, `object` no aparecen en nombres propios. Excepción: `info_dict` cuando se refiere literalmente al objeto de yt-dlp, y solo dentro de `media_extraction/`.
- **Sin nombres de patrón cuando no aportan intención** (#9): `JobStore` y no `JobRepository`; `MediaSource` y no `MediaGateway`.
- **Sin categorías técnicas como nombres de paquete** (#9): `domain`, `application`, `infrastructure`, `use_cases`, `utils`, `common`, `helpers` no se usan; cada paquete se llama como el componente que representa.
- **Sin argumentos booleanos que cambien el comportamiento**: si un flag elige entre dos acciones, son dos funciones (`request_cancellation` y `terminate_worker_running`).
- **Booleanos en positivo**: `has_active_download`, no `is_not_downloaded`.
- **Pronunciables** (#4): `QUEUED_MEDIA_DOWNLOADER_` como prefijo de variables de entorno, no `YTDLPGC_`.
- **Longitud según el alcance** (#5): nombres cortos solo en ámbitos muy pequeños (un índice de bucle); nombres completos en todo lo público.

## 7. Términos de terceros

Se conservan los nombres propios de herramientas externas cuando se habla de ellas, pero no se trasladan a nuestros nombres:

| Término externo | Dónde puede aparecer | Nuestro término |
|---|---|---|
| `info_dict`, `outtmpl`, `extract_flat` | Solo dentro de `media_extraction/` | playlist entry, output template, expansion |
| `download_archive` | No se usa ([ADR-0012](../notes/adr-0012-no-download-archive-no-database-triggers.md)) | media key en la base de datos |
| *Job Object* de Windows | Solo dentro de la implementación para Windows | process tree |
