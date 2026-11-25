# Plan de iteración E2: playlists, recuperación y cancelación

- **Fase RUP:** Elaboración
- **Iteración:** E2 de 2 (cierra la Elaboración; E3 solo si la evaluación deja riesgos sin neutralizar)
- **Inicio:** al integrar este plan en `main`
- **Duración:** delimitada por alcance: la iteración se cierra cuando T42 confirma los criterios de la sección 5 ([caso de desarrollo, §5](../process/development-case.md#5-roles-y-duración-de-las-iteraciones))
- **Estado:** en curso (enfoque híbrido, [ADR-0022](../notes/adr-0022-hybrid-approach-and-task-decomposition.md))

> **Cambio de estrategia (2026-11-25, decisión del Responsable).** La validación en Windows se hace **al final**, en una campaña única, cuando estén implementados **todos** los casos de uso (UC-01 a UC-10), no al cerrar cada iteración. Mientras tanto:
> - Se implementan los casos de uso con sus escenarios, y se ejecutan las pruebas posibles en el entorno de desarrollo (Linux).
> - Las pruebas `windows` se escriben y se trazan, pero no se ejecutan ni se cuentan como satisfactorias hasta la campaña.
> - Los resultados de Linux no se presentan como evidencia para Windows.
>
> Por eso UC-07 a UC-10 se incorporan a este plan (slice F, §4.6.1), la evaluación T42 se convierte en la campaña final (§7), y el estado de cada escenario se sigue en la matriz de la §8.

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

Los comandos `retry`, `list`, `show` y `purge` (UC-07 a UC-10) estaban fuera de E2; con el cambio de estrategia se implementan en el slice F (§4.6.1) antes de la campaña final.

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
| T32 | Reanudación con el formato guardado; A1 (reintento con el selector original), A2 (sin formato) | Agente | Contra un servidor local, una descarga con su `.part` continúa con una petición `Range`. **Hecha**; la recuperación tras una interrupción real queda en el criterio obligatorio de la [§5.1](#51-criterio-obligatorio-de-integración-entre-los-slices-b-y-c) ([seguimiento en ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md#seguimiento-de-t32-reanudación-verificada-2026-11-25)) | T31 |
| T44 | Propiedad de los archivos parciales de cada job (R-14) y respaldo de `JobCompleted` en el resultado de yt-dlp | Agente | Pruebas de regresión: nombres truncados, plantilla sin `%(id)s`, formatos abandonados, interrupción entre el formato nuevo y la limpieza. **Hecha** ([seguimiento en ADR-0010](../notes/adr-0010-sqlite-persistent-queue.md#seguimiento-de-t44-propiedad-de-los-archivos-de-cada-job-2026-11-25)) | T32 |

### 4.4 Slice C: terminar el árbol de procesos (ADR-0013)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T33 | Análisis de la implementación para Windows del `ProcessTreeTerminator` y decisión del Responsable (D1) | Agente, Responsable | ADR con la decisión. **Hecha**: D1 aprobada ([ADR-0029](../notes/adr-0029-process-tree-termination-on-windows.md)); el experimento en Windows pasa a la campaña final | — |
| T34 | Contrato `ProcessTreeTerminator` con implementación POSIX (grupo de procesos) y Windows según D1 | Agente | Prueba sobre hijo y nieto en cualquier sistema y prueba `windows`. **Hecha**: Linux ✔; 10 pruebas `windows` ⏳ ([seguimiento en ADR-0029](../notes/adr-0029-process-tree-termination-on-windows.md#seguimiento-de-t34-2026-11-25)) | T33 |
| T35 | El pool registra cada worker al arrancar y ofrece `terminate_worker_running(job_id)`, que termina su árbol y lo reemplaza | Agente | Prueba con un worker que lanza un subproceso, y el escenario de la [§5.1](#51-criterio-obligatorio-de-integración-entre-los-slices-b-y-c) automatizado. **Hecha**: Linux ✔; Windows ⏳ | T34 |

### 4.5 Slice D: cancelar (UC-05)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T36 | Comando `cancel` y `JobRequestInbox` sobre la tabla `job_requests`; A5 (sin `run` activo) y A7 (job terminado) | Agente | Pruebas del comando y de la bandeja. **Hecha**: Linux ✔ | — |
| T37 | `RunQueue` procesa las job requests en cada vuelta: A1 (`PENDING`), flujo básico (`RUNNING`) y A4 (playlist con sus hijos) | Agente | Pruebas con `ScriptedWorkerPool`. **Hecha**, con la cancelación cooperativa en el worker (hilo de cancelación y `JobCancelledError`): Linux ✔ | T36, T28 |
| T38 | Hilo de cancelación en el worker y `DownloadCancelled` en el hook de progreso; A2 (terminación forzada tras `cancellation_grace_seconds`) y A3 (termina antes de verlo) | Agente | Cancelar contra el servidor local, también durante la unión, sin procesos huérfanos. **Hecha**: Linux ✔ (yt-dlp real contra el servidor lento; job sin avances con un hijo, en lugar de una unión real); la cancelación durante una unión real con ffmpeg, en la campaña (paso 6) | T35, T37 |
| T39 | `Ctrl+C` en `run` (A6): el primero cancela los jobs en curso, el segundo termina los workers | Agente | Prueba con una señal al proceso de `run` | T38, T31 |

### 4.6 Slice E: operación de la cola

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T40 | `--keep-waiting` (UC-03 A5): `run` no termina y toma los jobs que se encolan después | Agente | Prueba de extremo a extremo con dos procesos | — |
| T41 | Reciclado de workers tras `max_jobs_per_worker` (UC-03 A6) y base de datos bloqueada en `enqueue` (UC-02 A3, código `1`, sin jobs a medias) | Agente | Pruebas del pool y del comando | T26 |

### 4.6.1 Slice F: casos de uso restantes (UC-07 a UC-10)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T45 | `retry JOB_ID... \| --all-failed` (UC-07): job request `RETRY`; `FAILED` y `CANCELLED` vuelven a `PENDING` e incrementan `attempt_count`; `SKIPPED` y `COMPLETED` no se reintentan | Agente | Pruebas del comando, de la bandeja y de `RunQueue` | T36, T37 |
| T46 | `list [--status STATUS] [--parent JOB_ID]` (UC-08): solo lectura | Agente | Pruebas del caso de uso y del comando | — |
| T47 | `show JOB_ID` (UC-09): todos los datos; en una playlist, resumen de hijos por estado | Agente | Pruebas del caso de uso y del comando | — |
| T48 | `purge [--completed] [--cancelled]` (UC-10): borra jobs terminados sin tocar los archivos descargados; sí borra la carpeta de parciales de cada job purgado (T44) | Agente | Pruebas del caso de uso y del comando | — |

### 4.7 Cierre

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T42 | Campaña final de validación en Windows (§7), incluida la medición de memoria que viene de E1 y el experimento de T33 | Evaluador | Los criterios de la sección 5 cumplidos; SUP-P04 fijado; matriz de la §8 con evidencia real; lista de riesgos actualizada | Todas, incluido el slice F |

### 4.8 Camino crítico

```text
T25 → T26 → T27 → T30 ─┐
T33 → T34 → T35 → T38 → T39 → T42
T31 → T32 → T44 ───────┘
T36 → T37 → T45 (slice F; T46 a T48 sin dependencias) → T42
```

Los slices A, B y C pueden avanzar en paralelo. T33 es el primer punto de decisión: conviene resolverlo pronto, porque la cancelación forzada depende de él.

### 4.9 Decisiones pendientes del Responsable

| ID | Decisión | Cuándo |
|---|---|---|
| D1 | Implementación para Windows del `ProcessTreeTerminator` (ADR-0013 dejó el contrato, no la implementación) | T33, **aprobada**: Job Object por worker y grupos de procesos en POSIX ([ADR-0029](../notes/adr-0029-process-tree-termination-on-windows.md)); validación en Windows en la campaña final |
| D2 | Una URL de un video dentro de una lista (`watch?v=…&list=…`): descargar solo el video o la lista entera. Por defecto, yt-dlp descarga la lista | T27, **resuelta**: solo el video ([ADR-0027](../notes/adr-0027-video-links-inside-lists.md)) |
| D3 | Plantilla por defecto de los hijos de una playlist (`playlist_output_template`): carpeta por playlist, índice y longitud | T29, **resuelta**: la del ejemplo de yt-dlp ([ADR-0028](../notes/adr-0028-playlist-child-output-template.md)) |

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
8. La recuperación ante una interrupción real pasa el escenario de la §5.1, automatizado y en Windows.

### 5.1 Criterio obligatorio de integración entre los slices B y C

T32 demostró la reanudación con un `.part` creado por la prueba. Aprobar T32 no demuestra la recuperación ante una interrupción real: hace falta terminar el worker y sus descendientes, que es el slice C. Este escenario es obligatorio para cerrar E2; se automatiza en T35 y se ejecuta en Windows en T42.

| Paso | Acción | Se verifica |
|---|---|---|
| 1 | Iniciar una descarga real contra un servidor de pruebas controlado, que sirve el contenido despacio | — |
| 2 | Interrumpirla cuando el servidor haya enviado una cantidad conocida de bytes | El `.part` tiene al menos esos bytes |
| 3 | Terminar el worker y sus procesos descendientes con el mecanismo de D1 | No queda ningún proceso del árbol |
| 4 | — | El job sigue `RUNNING` con su `selected_format_id`; el `.part` existe |
| 5 | Volver a ejecutar `run` | — |
| 6 | Recuperar el job con `RecoverInterruptedJobs` | El job pasa a `PENDING` y se envía |
| 7 | — | La única petición de descarga lleva `Range: bytes=<tamaño del .part>-` |
| 8 | — | El archivo final es idéntico al servido |
| 9 | — | El job queda `COMPLETED` con su `output_path` |
| 10 | — | No queda ningún proceso huérfano ni archivo parcial del job |

**Estado:**
- **Automatizado en T35** (`tests/job_queue/test_real_interruption_recovery.py`): pasos 1 a 10, con la interrupción hecha por `terminate_worker_running`. Linux ✔ (estable en 5 ejecuciones seguidas).
- **Windows ⏳:** la misma prueba, con el Job Object, en la campaña final (paso 3); y el paso manual con la muerte del proceso principal (`Stop-Process -Force` sobre `run`), que la prueba automatizada no cubre (paso 8).

## 6. Evaluación

*Se completa al cerrar la iteración.*

---

## 7. Campaña final de validación en Windows

Se ejecuta una sola vez, cuando la matriz de la §8 muestre todos los escenarios implementados. Es la tarea T42. La aceptación definitiva del proyecto depende de sus resultados reales.

### 7.1 Procedimiento

En un equipo físico con Windows 10 u 11 x64, Smart App Control desactivado ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)), Git con Git LFS y uv instalados.

| Paso | Qué se hace | Evidencia que se guarda |
|---|---|---|
| 1. Instalación | Clon nuevo de GitHub, `git lfs pull`, `uv sync` (UC-01 flujo básico) | Salida de los comandos |
| 2. Dependencias | `uv run queued-media-downloader diagnose` | Salida completa |
| 3. Suite automatizada | Las cinco comprobaciones; `uv run pytest -m windows`; `uv run pytest -m network` | Resumen de pytest: pasadas, fallidas y omitidas, por separado |
| 4. Experimento de T33 | `uv run python scripts/experiments/process_tree_termination.py --json doc/notes/experiments/t33-windows-results.json` | Tabla y JSON en [el documento del experimento](../notes/experiments/t33-process-tree-termination.md) |
| 5. Casos de uso | Cada escenario de la matriz (§8) marcado como pendiente en Windows, con el guion que se prepare para la campaña | Resultado por escenario en la matriz |
| 6. Procesos | Tras cada cancelación, interrupción y cierre: ningún proceso de ffmpeg, deno ni worker (`Get-Process`) | Salida de `Get-Process` |
| 7. Cierres | Cierre normal de `run`; `Ctrl+C` una y dos veces; cierre de la ventana de la terminal; `run` terminado con `Stop-Process -Force` | Estado de los jobs (`list`) y procesos vivos |
| 8. Interrupción real (§5.1) | El escenario obligatorio entre los slices B y C, automatizado en T35 | Resultado de la prueba y del paso manual |
| 9. Cambio de formato | Reanudar un job cuyo formato guardado ya no existe (UC-06 A1) | Formato guardado antes y después; parciales restantes |
| 10. Integridad | Comparar los archivos descargados con `ffprobe` y su tamaño | Salida de `ffprobe` |
| 11. Aislamiento | Dos jobs concurrentes con nombres que coinciden tras el recorte (R-14) | Archivos de cada job |
| 12. Estado | La base de datos tras cada paso no tiene jobs `RUNNING` sin worker | Salida de `list` |
| 13. Memoria | Medición de RSS (R-02, criterio 6, SUP-P04) | Valores máximos por proceso |

Cada defecto encontrado se registra en la §6, se corrige en una tarea nueva con su prueba de regresión y se repite el paso afectado.

### 7.2 Requisitos de Windows reunidos durante la implementación

Se amplía con cada tarea. Cada uno se verifica en la campaña.

| Requisito | Origen | Prueba prevista |
|---|---|---|
| Job Object por worker: sin huérfanos al terminar el árbol, al caer el worker y al morir `run`; sin escape por `CREATE_BREAKAWAY_FROM_JOB`; handle no heredable | ADR-0029, T34 | Experimento de T33; `pytest -m windows` (`tests/workers/test_process_tree_terminator.py`, 10 pruebas) y T35 |
| `Ctrl+C` llega también a los workers y a ffmpeg (mismo grupo de consola) | ADR-0029, hallazgo 4 | T39 y paso 7 |
| Cancelar durante una unión real de ffmpeg termina ffmpeg tras el plazo y no deja procesos | UC-05 A2, T38 | Paso 6 |
| La carpeta de parciales de un job (`.partial\job-N`) se mueve al terminar sin copiar y se borra; rutas largas con la carpeta añadida | T44 | Pasos 9 y 11 |
| Rutas largas y nombres de playlist con caracteres no válidos | R-10, ADR-0028 | Paso 5 (UC-04) |

---

## 8. Matriz de casos de uso: implementación y validación

Estado al 2026-11-25. Se actualiza al integrar cada tarea.

Leyenda de pruebas:
- **Linux ✔:** automatizada y ejecutada con éxito en el entorno de desarrollo.
- **Windows ⏳:** escrita o prevista para Windows y aún **no ejecutada**. No cuenta como satisfactoria.
- **Windows E1 ✔:** ejecutada con éxito en la evaluación de E1, en Windows 11; se repite en la campaña.

La aceptación final de todos los escenarios queda **pendiente** de la campaña (§7).

### UC-01 Instalar y verificar el entorno

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico | E1 (T05–T12) | Hecha | Linux ✔; Windows E1 ✔ (`diagnose`) | Repetir en la campaña (paso 1–2) |
| A1 Sin Git LFS / A5 binario corrupto | E1 | Hecha | Linux ✔ (punteros LFS, checksums) | Paso 2 con un clon sin LFS |
| A2 Cuota de LFS agotada | E1 | Documentada | — | Manual, si se puede reproducir |
| A3 Plataforma no soportada | E1 | Hecha | Linux ✔ | — |
| A4 ffmpeg desde `PATH` | E1 | Hecha | Linux ✔ | Paso 2 |
| A6 Configuración no válida | E1 | Hecha | Linux ✔; Windows E1 ✔ | — |
| A7 Smart App Control | T19 | Documentada (ADR-0026) | Windows E1 ✔ (detectado y documentado) | Paso 1 |

### UC-02 Encolar contenido

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico, `--audio-only`, `--format`, `--playlist` | E1, T23, T43 | Hecha | Linux ✔; Windows E1 ✔ (sin `--playlist`) | Paso 5 con `--playlist` |
| A1 URL no válida | E1 | Hecha | Linux ✔ | — |
| A2 `run` en otra terminal | E1 | Hecha (WAL) | Linux ✔ | Paso 5 con dos terminales |
| A3 Base de datos bloqueada | T41 | **Pendiente** | — | Paso 5 |

### UC-03 Descargar un contenido

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico con unión | E1 | Hecha | Linux ✔; Windows E1 ✔ | Pasos 5 y 10 |
| A1 Duplicado | E1, T21, T23 | Hecha | Linux ✔; Windows E1 ✔ | — |
| A2 Fallos de red, no disponible, geo, no soportada | E1, T24 | Hecha | Linux ✔; Windows E1 ✔ (fallo controlado) | — |
| A3 Extractor desactualizado | E1 | Hecha | Linux ✔ | — |
| A4 Worker muere sin evento final | E1 (T20), T35 | Hecha; sus descendientes se terminan antes de sustituirlo (T35) | Linux ✔ | Pasos 5 y 6 |
| A5 `--keep-waiting` | T40 | **Pendiente** | — | Paso 5 |
| A6 Reciclado de workers | T41 | **Pendiente** | — | Paso 5 |

### UC-04 Expandir una playlist

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico (perezosa, por lotes, carpeta por playlist) | T25–T30 | Hecha | Linux ✔ (servidor local); `network` ⏳ (canal grande, R-06) | Pasos 3 y 5 con YouTube; memoria (paso 13) |
| A1 Playlist anidada | T27, T28 | Hecha | Linux ✔ | Paso 5 |
| A2 Duplicada | T28, T30 | Hecha | Linux ✔, con 1 y 2 workers | Paso 5 |
| A3 No disponible | T27, T28 | Hecha | Linux ✔ | Paso 5 |
| A4 `multi_video` | T27 | Hecha (se expande como playlist) | Linux ✔ | — |
| A5 Cancelación durante la expansión | T37, T38 | Hecha: la expansión se detiene en su siguiente lote y no crea más hijos | Linux ✔ (dobles) | Paso 5 |
| A6 Fallo a mitad de la expansión | T27; reintento con T45 | Fallo hecho; reintento **pendiente** | Linux ✔ (fallo) | Paso 5 |
| Video dentro de una lista (`--playlist`) | T27, T43 | Hecha | Linux ✔; `network` ⏳ | Paso 3 |

### UC-05 Cancelar un job

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico (cooperativa) | T36, T37, T38 | Hecha: `CANCELLATION_REQUESTED`, petición al worker, `JobCancelled` en el siguiente avance; el `.part` se conserva | Linux ✔ (también con yt-dlp real contra el servidor lento) | Pasos 5 y 6 |
| A1 `PENDING` | T37 | Hecha | Linux ✔ | — |
| A2 Terminación forzada | T34, T35, T38 | Hecha: tras `cancellation_grace_seconds` (10 s), el árbol del worker se termina y el job queda `CANCELLED`; los mensajes tardíos se ignoran | Linux ✔ (job sin avances con un hijo) | Experimento de T33; `windows` de T34; paso 6 con una unión real de ffmpeg |
| A3 Termina antes de ver la bandera | T37 | Hecha: `JobCompleted` gana; cualquier otro final confirma la cancelación | Linux ✔ | — |
| A4 Playlist con sus hijos | T36, T37 | Hecha: registro (T36); en `run`, también los hijos creados después y sin nuevos hijos de un lote tardío (T37) | Linux ✔ | Paso 5 |
| A5 Sin `run` activo | T36, T37 | Hecha | Linux ✔ | — |
| A6 `Ctrl+C` | T39 | **Pendiente** | — | Paso 7 |
| A7 Job terminado | T36, T37 | Hecha en `cancel` y en `run` | Linux ✔ | — |

### UC-06 Recuperar la cola y reanudar descargas

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Recuperación al arrancar | T31 | Hecha | Linux ✔ | Paso 7 |
| Reanudación con `Range` | T32, T44 | Hecha con un `.part` creado por la prueba, en la carpeta de parciales del job | Linux ✔ | Paso 8 |
| Interrupción real (§5.1) | T35, T42 | Hecha y automatizada (T35) | Linux ✔ | Pasos 3 y 8 (obligatorio), incluida la muerte del proceso principal |
| A1 Formato ya no disponible | T32, T44 | Hecha | Linux ✔ | Paso 9 |
| Propiedad de los parciales y del archivo final (R-14) | T44 | Hecha | Linux ✔ (nombres truncados, plantilla sin `%(id)s`, archivo final compartido) | Paso 11 |
| A2 Sin formato guardado | E1, T32 | Hecha | Linux ✔ | — |
| A3 Parciales borrados por el User | T32 | Hecha (yt-dlp descarga de cero) | Linux ✔ (sin `.part`) | — |

### UC-07 a UC-10

| Caso de uso | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| UC-07 Reintentar un job | T45 | **Pendiente** | — | Paso 5 |
| UC-08 Listar jobs | T46 | **Pendiente** | — | Paso 12 |
| UC-09 Ver un job | T47 | **Pendiente** | — | Paso 5 |
| UC-10 Purgar jobs terminados | T48 | **Pendiente** | — | Paso 5 |

### Riesgos y dependencias abiertos

| Riesgo | Afecta a | Se cierra con |
|---|---|---|
| R-02 Memoria | UC-03, UC-04 | Paso 13 de la campaña |
| R-04 Árbol de procesos | UC-03 A4, UC-05 A2, UC-06 | T34 y T35 hechas (Linux ✔); pasos 3, 4, 6 y 8 de la campaña |
| R-05 Reanudación | UC-06 | §5.1 automatizado en T35 (Linux ✔) y paso 8 |
| R-06 Iteración perezosa | UC-04 | Prueba `network` y paso 13 |
| R-14 Nombres compartidos entre jobs | UC-03, UC-06 | T44 (hecha, Linux ✔) y paso 11 |
