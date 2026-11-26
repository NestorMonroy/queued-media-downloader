# Diseño — Parte 0: vocabulario del proyecto

- **Estado:** Borrador para revisión
- **Fecha:** 2026-11-22
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
| **interruption** (interrupción) | `Ctrl+C` durante `run`: detiene la cola sin cancelar ningún job; los jobs en curso conservan su estado y sus parciales y continúan en el siguiente `run` | cancel (no es una cancelación) |

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
