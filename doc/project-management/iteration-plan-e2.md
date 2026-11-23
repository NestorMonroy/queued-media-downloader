# Plan de iteración E2: playlists, recuperación y cancelación

- **Fase RUP:** Elaboración
- **Iteración:** E2 de 2 (cierra la Elaboración; E3 solo si la evaluación deja riesgos sin neutralizar)
- **Inicio:** al integrar este plan en `main`
- **Duración:** delimitada por alcance: la iteración se cierra cuando T42 confirma los criterios de la sección 5 ([caso de desarrollo, §5](../process/development-case.md#5-roles-y-duración-de-las-iteraciones))
- **Estado:** planificada (enfoque híbrido, [ADR-0022](../notes/adr-0022-hybrid-approach-and-task-decomposition.md))

---

## 1. Objetivo

Completar los casos de uso significativos que quedan para que la arquitectura soporte una cola real: **descargar playlists, sobrevivir a un cierre inesperado y cancelar sin dejar procesos huérfanos**, en Windows. Con E2 se alcanza el hito de la Elaboración: los seis casos de uso significativos funcionan de extremo a extremo.

## 2. Alcance

| Caso de uso | Escenarios incluidos | Escenarios excluidos |
|---|---|---|
| [UC-04](../requirements/use-cases/uc-04-expand-playlist.md) | Flujo básico; A1 (playlists anidadas); A2 (duplicados); A3 (no disponibles); A5 (cancelación durante la expansión, con UC-05); A6 (fallo a mitad de la expansión) | El reintento de A6, que depende de `retry` (UC-07) |
| [UC-05](../requirements/use-cases/uc-05-cancel-job.md) | Flujo básico; A1 a A7 | — |
| [UC-06](../requirements/use-cases/uc-06-recover-and-resume-queue.md) | Flujo básico; A1 a A3 | — |
| [UC-03](../requirements/use-cases/uc-03-download-single-media.md) | A5 (`--keep-waiting`); A6 (reciclado de workers) | — (A1, A3 y A4 se adelantaron en E1) |
| [UC-02](../requirements/use-cases/uc-02-enqueue-media.md) | A3 (base de datos bloqueada) | — |

Fuera de E2: los comandos `retry`, `list`, `show` y `purge` (UC-07 a UC-10, Construcción).

Viene de E1: el criterio 6 (memoria máxima y SUP-P04), que se mide en la evaluación de E2.

## 3. Riesgos que neutraliza

| Riesgo | Cómo se comprueba en E2 |
|---|---|
| R-02 Consumo de memoria | Medición en Windows durante una descarga con unión y durante la expansión de una playlist |
| R-04 Árbol de procesos | Prueba `windows` del terminador sobre hijos y nietos; cancelar durante la unión sin procesos huérfanos |
| R-05 Reanudación | Interrumpir una descarga contra el servidor local y comprobar que continúa desde el `.part` con el mismo formato |
| R-06 Iteración perezosa de playlists | Prueba con un canal grande (marcador `network`): la memoria del worker no crece con el número de entradas |
| R-10 Antivirus y rutas largas | Verificación manual en Windows con nombres de playlist largos |

## 4. Trabajo

### 4.1 Cómo se descompone

Igual que en E1 ([ADR-0022](../notes/adr-0022-hybrid-approach-and-task-decomposition.md)): un slice por capacidad que el usuario puede probar tras `git pull`, y cada tarea con su prueba escrita antes del código. La numeración de tareas continúa la de E1.

### 4.2 Slice A: playlists (UC-04)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T25 | `Job` con `parent_id` y `PlaylistContext`; `SqliteJobStore` los guarda en las columnas que ya existen | Agente | Ida y vuelta de un job hijo por la base de datos | — |
| T26 | Job event `PlaylistEntriesFound` (lote de playlist entries serializable) y `JobStore.create_many` en una sola transacción | Agente | Prueba de serialización entre procesos; un lote con un duplicado no deja hijos a medias | T25 |
| T27 | `YtDlpMediaSource.expand` recorre las entradas de forma perezosa por lotes; entradas que son playlists (A1) y no disponibles (A3) | Agente | Contra el servidor local, una playlist de N entradas publica sus lotes y `JobCompleted` | T26 |
| T28 | `JobEventApplier` crea los hijos: duplicados (A2) y no disponibles (A3) como `SKIPPED`, anidadas como `EXPANSION` | Agente | Pruebas con `ScriptedWorkerPool` e `InMemoryJobStore` | T26 |
| T29 | `output_template_builder` y `playlist_output_template`: escapado de `%`, saneado y longitud, con reglas de Windows | Agente | Pruebas con `PureWindowsPath` | T25 |
| T43 | Opción `enqueue --playlist`: con un enlace a un video dentro de una lista, descarga la lista entera ([ADR-0027](../notes/adr-0027-video-links-inside-lists.md)) | Agente | La opción se guarda con el job y cambia `noplaylist`; prueba `network` con el enlace real | T27 |
| T30 | `enqueue` + `run` de una playlist de extremo a extremo; prueba `network` de iteración perezosa (R-06) | Agente | Una playlist local se descarga entera en carpetas por playlist | T27, T28, T29 |

### 4.3 Slice B: recuperar y reanudar (UC-06)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T31 | `recover_interrupted_jobs` al arrancar `run`: `RUNNING` → `PENDING`, `CANCELLATION_REQUESTED` → `CANCELLED` | Agente | Pruebas con `InMemoryJobStore` | — |
| T32 | Reanudación con el formato guardado; A1 (reintento con el selector original), A2 (sin formato) | Agente | Contra un servidor local lento, una descarga interrumpida continúa con una petición `Range` | T31 |

### 4.4 Slice C: terminar el árbol de procesos (ADR-0013)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T33 | Análisis de la implementación para Windows del `ProcessTreeTerminator` y decisión del Responsable (D1) | Agente, Responsable | ADR con la decisión | — |
| T34 | Contrato `ProcessTreeTerminator` con implementación POSIX (grupo de procesos) y Windows según D1 | Agente | Prueba sobre hijo y nieto en cualquier sistema y prueba `windows` | T33 |
| T35 | El pool registra cada worker al arrancar y ofrece `terminate_worker_running(job_id)`, que termina su árbol y lo reemplaza | Agente | Prueba con un worker que lanza un subproceso | T34 |

### 4.5 Slice D: cancelar (UC-05)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T36 | Comando `cancel` y `JobRequestInbox` sobre la tabla `job_requests`; A5 (sin `run` activo) y A7 (job terminado) | Agente | Pruebas del comando y de la bandeja | — |
| T37 | `RunQueue` procesa las job requests en cada vuelta: A1 (`PENDING`), flujo básico (`RUNNING`) y A4 (playlist con sus hijos) | Agente | Pruebas con `ScriptedWorkerPool` | T36, T28 |
| T38 | Hilo de cancelación en el worker y `DownloadCancelled` en el hook de progreso; A2 (terminación forzada tras `cancellation_grace_seconds`) y A3 (termina antes de verlo) | Agente | Cancelar contra el servidor local, también durante la unión, sin procesos huérfanos | T35, T37 |
| T39 | `Ctrl+C` en `run` (A6): el primero cancela los jobs en curso, el segundo termina los workers | Agente | Prueba con una señal al proceso de `run` | T38, T31 |

### 4.6 Slice E: operación de la cola

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T40 | `--keep-waiting` (UC-03 A5): `run` no termina y toma los jobs que se encolan después | Agente | Prueba de extremo a extremo con dos procesos | — |
| T41 | Reciclado de workers tras `max_jobs_per_worker` (UC-03 A6) y base de datos bloqueada en `enqueue` (UC-02 A3, código `1`, sin jobs a medias) | Agente | Pruebas del pool y del comando | T26 |

### 4.7 Cierre

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T42 | Evaluación en Windows con el guion de E2, incluida la medición de memoria que viene de E1 | Evaluador | Los criterios de la sección 5 cumplidos; SUP-P04 fijado; lista de riesgos actualizada | Todas |

### 4.8 Camino crítico

```text
T25 → T26 → T27 → T30 ─┐
T33 → T34 → T35 → T38 → T39 → T42
T31 → T32 ─────────────┘
```

Los slices A, B y C pueden avanzar en paralelo. T33 es el primer punto de decisión: conviene resolverlo pronto, porque la cancelación forzada depende de él.

### 4.9 Decisiones pendientes del Responsable

| ID | Decisión | Cuándo |
|---|---|---|
| D1 | Implementación para Windows del `ProcessTreeTerminator` (ADR-0013 dejó el contrato, no la implementación) | T33 |
| D2 | Una URL de un video dentro de una lista (`watch?v=…&list=…`): descargar solo el video o la lista entera. Por defecto, yt-dlp descarga la lista | T27, **resuelta**: solo el video ([ADR-0027](../notes/adr-0027-video-links-inside-lists.md)) |
| D3 | Plantilla por defecto de los hijos de una playlist (`playlist_output_template`): carpeta por playlist, índice y longitud | T29 |

---

## 5. Criterios de evaluación

La iteración se considera cumplida si:

1. Las cinco comprobaciones locales pasan, también en Windows.
2. `uv run pytest -m windows` pasa en el entorno Windows, incluidas las pruebas del terminador de procesos.
3. Una playlist real de YouTube se encola y se descarga entera; sus duplicados quedan `SKIPPED`.
4. Cancelar un job durante la descarga y durante la unión lo deja `CANCELLED` y no queda ningún proceso de ffmpeg, deno ni worker.
5. Cerrar `run` a la fuerza a mitad de una descarga y volver a ejecutarlo continúa desde lo descargado.
6. La memoria máxima del proceso principal, del worker y de ffmpeg está medida, y SUP-P04 queda fijado (viene de E1).
7. La memoria del worker no crece al expandir una playlist grande (R-06).

## 6. Evaluación

*Se completa al cerrar la iteración.*
