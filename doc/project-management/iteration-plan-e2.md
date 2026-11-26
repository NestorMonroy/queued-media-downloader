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
| T39 | `Ctrl+C` en `run` (A6): el primero detiene los jobs en curso sin cancelarlos, el segundo termina los workers (el enunciado original decía "cancela"; se corrigió al implementar, de acuerdo con ADR-0029) | Agente | Prueba con una señal al proceso de `run`. **Hecha**: el primero detiene los jobs **sin cancelarlos** (siguen `RUNNING` y se reanudan, como pide A6 y ADR-0029); el segundo termina los árboles ya; código 130. Linux ✔ (señales reales); Windows ⏳ (paso 7) | T38, T31 |

### 4.6 Slice E: operación de la cola

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T40 | `--keep-waiting` (UC-03 A5): `run` no termina y toma los jobs que se encolan después | Agente | Prueba de extremo a extremo con dos procesos. **Hecha**: termina con `Ctrl+C` (código 130). Linux ✔ | — |
| T41 | Reciclado de workers tras `max_jobs_per_worker` (UC-03 A6) y base de datos bloqueada en `enqueue` (UC-02 A3, código `1`, sin jobs a medias) | Agente | Pruebas del pool y del comando. **Hecha**: `enqueue` pasa a una sola transacción (antes una por URL, que podía dejar jobs a medias). Linux ✔ | T26 |

### 4.6.1 Slice F: casos de uso restantes (UC-07 a UC-10)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T45 | `retry JOB_ID... \| --all-failed` (UC-07): job request `RETRY`; `FAILED` y `CANCELLED` vuelven a `PENDING` e incrementan `attempt_count`; `SKIPPED` y `COMPLETED` no se reintentan | Agente | Pruebas del comando, de la bandeja y de `RunQueue`. **Hecha**: reintentar una expansión trae también a sus descendientes fallidos o cancelados. Linux ✔ | T36, T37 |
| T46 | `list [--status STATUS] [--parent JOB_ID]` (UC-08): solo lectura | Agente | Pruebas del caso de uso y del comando. **Hecha**: Linux ✔ | — |
| T47 | `show JOB_ID` (UC-09): todos los datos; en una playlist, resumen de hijos por estado | Agente | Pruebas del caso de uso y del comando. **Hecha**: Linux ✔ | — |
| T48 | `purge [--completed] [--cancelled]` (UC-10): borra jobs terminados sin tocar los archivos descargados; sí borra la carpeta de parciales de cada job purgado (T44) | Agente | Pruebas del caso de uso y del comando. **Hecha**: sin opciones purga ambos estados; una playlist con entradas sin terminar se conserva, porque borrarla arrastraría a sus entradas (`ON DELETE CASCADE`). Linux ✔ | — |

### 4.7 Cierre

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T51 | Corrección de los defectos de la primera ejecución en Windows y validación sin etiquetas: T42-D1 (prueba), T42-D2 (experimento), T42-D3 (yt-dlp 2026.11.23 con el [procedimiento SUP-S01](../process/yt-dlp-update-procedure.md)); `diagnose` informa de yt-dlp y yt-dlp-ejs; `scripts/windows/validation_campaign.ps1` identifica cada ejecución por el commit de `main`; `scripts/check_commit_message.py` dentro del proyecto | Agente | Linux ✔; Windows ✔ (T42-D1, D2 y D3 confirmados, [registro](t42-results.md)) | T50 |
| T50 | Consolidación del candidato T42: owner token en reclamaciones y parciales (base de datos restaurada), migración 0004 (propiedad sin decidir de un archivo reclamado varias veces), arranque de workers que falla al registrarse, guion y script de la campaña revisados, etiqueta `t42-candidate-1` publicada | Agente | Correcciones con sus pruebas y verificación de desarrollo sobre el commit etiquetado. **Hecha**: Linux ✔; Windows ⏳ (T42) | T49 |
| T49 | Auditoría integral previa a la aceptación: trazabilidad por requisito, especificación completa de UC-07 a UC-10, aislamiento de las pruebas, propiedad de los archivos finales ([ADR-0030](../notes/adr-0030-final-file-ownership-claims.md)), contrato de `JobCompleted`, migraciones, `Ctrl+C` repetidos, cola ocupada en todos los comandos y preparación de T42 | Agente | Correcciones con sus pruebas, verificación de desarrollo y [informe de la auditoría](pre-acceptance-audit.md). **Hecha**: Linux ✔; deja `READY_FOR_WINDOWS_VALIDATION` | T45–T48 |
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

**Guion paso a paso, con las órdenes y el registro de resultados:** [windows-validation-campaign.md](windows-validation-campaign.md).

### 7.1 Procedimiento

En un equipo físico con Windows 10 u 11 x64, Smart App Control desactivado ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)), Git con Git LFS y uv instalados.

| Paso | Qué se hace | Evidencia que se guarda |
|---|---|---|
| 1. Instalación | Clon nuevo de GitHub, `git lfs pull`, `uv sync` (UC-01 flujo básico) | Salida de los comandos |
| 2. Dependencias | `uv run queued-media-downloader diagnose` | Salida completa |
| 3. Suite automatizada | Las cinco comprobaciones; `uv run pytest -m windows`; `uv run pytest -m network` | Resumen de pytest: pasadas, fallidas y omitidas, por separado |
| 4. Experimento de T33 | `uv run python scripts/experiments/process_tree_termination.py --json doc/notes/experiments/t33-windows-results.json` | Tabla y JSON en [el documento del experimento](../notes/experiments/t33-process-tree-termination.md) |
| 5. Casos de uso | Cada escenario de la matriz (§8) marcado como pendiente en Windows, con el [guion de la campaña](windows-validation-campaign.md#paso-5-casos-de-uso) | Resultado por escenario en la matriz |
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
| `Ctrl+C` llega también a los workers y a ffmpeg (mismo grupo de consola): el worker llama a `SetConsoleCtrlHandler(NULL, TRUE)`, que heredan sus hijos | ADR-0029, hallazgo 4; T39 | Paso 7: un `Ctrl+C` durante una unión real no debe abortar ffmpeg ni marcar el job `FAILED` |
| Cancelar durante una unión real de ffmpeg termina ffmpeg tras el plazo y no deja procesos | UC-05 A2, T38 | Paso 6 |
| La carpeta de parciales de un job (`.partial\job-N`) se mueve al terminar sin copiar y se borra; rutas largas con la carpeta añadida | T44 | Pasos 9 y 11 |
| Rutas largas y nombres de playlist con caracteres no válidos | R-10, ADR-0028 | Paso 5 (UC-04) |

---

## 8. Matriz de casos de uso: implementación y validación

Estado al 2026-11-26, tras la auditoría previa a la aceptación (T49), la consolidación del candidato (T50) y las correcciones de la primera ejecución en Windows (T51): **todos los escenarios de UC-01 a UC-10 están implementados y probados en Linux**. Lo que falta es la validación en Windows, en la campaña (§7). Se actualiza con la evidencia de la campaña.

| Estado del producto ([caso de desarrollo, §3](../process/development-case.md#estados-del-producto-cinco-conceptos-distintos)) | Valor | Evidencia |
|---|---|---|
| Implementación | `IMPLEMENTATION_COMPLETE` | Esta matriz |
| Verificación de desarrollo | `DEVELOPMENT_VERIFICATION_PASSED` | `scripts/run_checks.py` sobre el commit publicado (§8.3) |
| Validación en Windows | `WINDOWS_VALIDATION_PENDING` | Campaña T42 en curso: [registro de resultados](t42-results.md) |
| Evaluación de E2 | Pendiente | §6, tras la campaña |
| Aceptación final | `FINAL_ACCEPTANCE_PENDING` | Decisión del Responsable con los resultados de Windows |

Leyenda de pruebas:
- **Linux ✔:** automatizada y ejecutada con éxito en el entorno de desarrollo.
- **Windows ⏳:** escrita o prevista para Windows y aún **no ejecutada**. No cuenta como satisfactoria.
- **Windows E1 ✔:** ejecutada con éxito en la evaluación de E1 (2026-11-23), en Windows 11, sobre la build de E1. Se conserva como evidencia de E1; **no valida la build actual** y se repite en la campaña.
- **No ejecutable aquí:** escrita, pero el entorno de desarrollo no la permite (por ejemplo, el proxy rechaza YouTube); se ejecuta en la campaña.

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
| A8 Base de datos que no se abre o migración fallida | T49 | Hecha: rollback, cierre de la conexión y error sin traza (código 1; `diagnose` la marca fallida) | Linux ✔ (migración rota simulada, archivo que no es SQLite, actualización desde las versiones 1 y 2) | Paso 2 (esquema 3) |
| A7 Smart App Control | T19 | Documentada (ADR-0026) | Windows E1 ✔ (detectado y documentado) | Paso 1 |

### UC-02 Encolar contenido

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico, `--audio-only`, `--format`, `--playlist` | E1, T23, T43 | Hecha | Linux ✔; Windows E1 ✔ (sin `--playlist`) | Paso 5 con `--playlist` |
| A1 URL no válida | E1 | Hecha | Linux ✔ | — |
| A2 `run` en otra terminal | E1 | Hecha (WAL) | Linux ✔ | Paso 5 con dos terminales |
| A3 Base de datos bloqueada | T41, T49 | Hecha: código 1, ningún job creado; también en `cancel`, `retry` y `purge` (T49) | Linux ✔ (bloqueo real de otra conexión) | Paso 5.7 |

### UC-03 Descargar un contenido

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico con unión | E1 | Hecha | Linux ✔; Windows E1 ✔ | Pasos 5 y 10 |
| A1 Duplicado | E1, T21, T23 | Hecha | Linux ✔; Windows E1 ✔ | — |
| A2 Fallos de red, no disponible, geo, no soportada | E1, T24 | Hecha | Linux ✔; Windows E1 ✔ (fallo controlado) | — |
| A3 Extractor desactualizado | E1 | Hecha | Linux ✔ | — |
| A4 Worker muere sin evento final | E1 (T20), T35 | Hecha; sus descendientes se terminan antes de sustituirlo (T35) | Linux ✔ | Pasos 5 y 6 |
| Worker que muere mientras se registra en su terminador (Job Object) | T50 | Hecha: hasta 3 intentos; si todos fallan, `run` termina cada árbol de inmediato, informa con código 1 y los jobs en curso se recuperan en el siguiente `run` | Linux ✔ (dobles: `FakeProcessTreeTerminator`) | Criterio explícito de la campaña (comportamiento nativo) |
| A5 `--keep-waiting` | T40 | Hecha; se termina con `Ctrl+C` | Linux ✔ (dos procesos reales) | Paso 5 |
| A6 Reciclado de workers | T41 | Hecha (`max_jobs_per_worker`, 20 por defecto) | Linux ✔ (procesos reales) | Paso 5 y memoria (paso 13) |
| A7 Nombre final de otro job o archivo ajeno | T49 (ADR-0030) | Hecha: reclamación antes de descargar; falla con `FILESYSTEM` sin tocar el archivo | Linux ✔ (huella de tamaño, fecha y SHA-256; dos jobs a la vez); `windows` ⏳ (mayúsculas, separadores, ruta larga, archivo abierto) | Paso 11 (obligatorio) |
| A8 Descarga sin archivo final utilizable; contrato de `JobCompleted` | T32, T49 | Hecha: `FAILED` con `FILESYSTEM`; `Job.complete` exige ruta a una descarga y ninguna a una expansión | Linux ✔ | — |

### UC-04 Expandir una playlist

| Escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| Flujo básico (perezosa, por lotes, carpeta por playlist) | T25–T30 | Hecha | Linux ✔ (servidor local); `network` ⏳ (canal grande, R-06) | Pasos 3 y 5 con YouTube; memoria (paso 13) |
| A1 Playlist anidada | T27, T28 | Hecha | Linux ✔ | Paso 5 |
| A2 Duplicada | T28, T30 | Hecha | Linux ✔, con 1 y 2 workers | Paso 5 |
| A3 No disponible | T27, T28 | Hecha | Linux ✔ | Paso 5 |
| A4 `multi_video` | T27 | Hecha (se expande como playlist) | Linux ✔ | — |
| A5 Cancelación durante la expansión | T37, T38 | Hecha: la expansión se detiene en su siguiente lote y no crea más hijos | Linux ✔ (dobles) | Paso 5 |
| A6 Fallo a mitad de la expansión | T27, T45 | Hecha: el reintento vuelve a expandir y los duplicados quedan `SKIPPED` | Linux ✔ | Paso 5 |
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
| A6 `Ctrl+C` | T39, T49 | Hecha: el primero detiene la cola y deja los jobs para reanudarse; el segundo termina ya; los siguientes se ignoran hasta que `run` sale (T49); el worker y sus hijos ignoran `Ctrl+C` | Linux ✔ (`SIGINT` real al proceso de `run`, uno, dos y seis seguidos; reanudación con `Range`) | Paso 7, casos a–f (en Windows es un evento de consola que llega a todos los procesos) |
| A7 Job terminado (`COMPLETED`, `FAILED`, `SKIPPED`, `CANCELLED`) | T36, T37, T49 | Hecha en `cancel` y en `run`; un `FAILED` conserva su motivo | Linux ✔ | — |
| A8 Job `CANCELLATION_REQUESTED` | T37 | Hecha (sin cambios) | Linux ✔ | — |

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
| A4 Cierre tras mover el archivo final | T44, T49 | Hecha: el job reconoce su reclamación y su archivo | Linux ✔ | Paso 8 |
| A6 Migración pendiente o fallida al arrancar | T49 | Hecha (rollback; `run` no ejecuta nada) | Linux ✔ | Paso 2 |
| A7 Base de E1 con un archivo reclamado por varios jobs | T49, T50 | Hecha: ningún dueño, todos `FAILED` con diagnóstico, archivo intacto (migración 0004, también sobre bases que ya tenían la 0003) | Linux ✔ | — |
| A8 Base de datos restaurada de una copia anterior | T50 | Hecha: owner token; un id reutilizado no hereda reclamaciones ni parciales (se apartan, sin borrar) | Linux ✔ | — |

### UC-07 a UC-10

| Caso de uso | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
Especificaciones completas desde T49 ([UC-07](../requirements/use-cases/uc-07-retry-job.md), [UC-08](../requirements/use-cases/uc-08-list-jobs.md), [UC-09](../requirements/use-cases/uc-09-show-job.md), [UC-10](../requirements/use-cases/uc-10-purge-finished-jobs.md)).

| Caso de uso y escenario | Tareas | Implementación | Pruebas | Pendiente en Windows |
|---|---|---|---|---|
| UC-07 flujo básico, A1 `--all-failed`, A2 no reintentable, E1–E2 | T45 | Hecha (conserva formato y parciales para reanudar) | Linux ✔ | Paso 5.6 |
| UC-07 A3 playlist e idempotencia (A4) | T45, T49 | Hecha: entradas `FAILED`/`CANCELLED` sí, `COMPLETED` no; peticiones repetidas, un intento | Linux ✔ | Paso 5.6 |
| UC-07 E3 base de datos ocupada | T49 | Hecha | Linux ✔ | Paso 5.7 |
| UC-08 filtros, cola vacía, E1–E2 | T46 | Hecha | Linux ✔ | Paso 12 |
| UC-09 job, hijo, fallo, playlist, E1 | T47 | Hecha | Linux ✔ | Paso 5.2 |
| UC-10 flujo básico (sin opciones: `COMPLETED` y `CANCELLED`), A1, A2 y combinaciones | T48, T49 | Hecha | Linux ✔ | Paso 5.6 |
| UC-10 parciales y reclamaciones; E1 sin cambios con la base ocupada | T48, T49 | Hecha: primero la base de datos, después los parciales y las reclamaciones huérfanas | Linux ✔ | Pasos 5.6, 5.7 y 11 |

### Riesgos y dependencias abiertos

| Riesgo | Afecta a | Se cierra con |
|---|---|---|
| R-02 Memoria | UC-03, UC-04 | Paso 13 de la campaña |
| R-04 Árbol de procesos | UC-03 A4, UC-05 A2, UC-06 | T34 y T35 hechas (Linux ✔); pasos 3, 4, 6 y 8 de la campaña |
| R-05 Reanudación | UC-06 | §5.1 automatizado en T35 (Linux ✔) y paso 8 |
| R-06 Iteración perezosa | UC-04 | Prueba `network` y paso 13 |
| R-14 Nombres compartidos entre jobs | UC-03, UC-06 | T44 y T49/ADR-0030 (hechas, Linux ✔) y paso 11 |
| R-10 Antivirus y rutas largas | UC-03, UC-06 | Pruebas `windows` de T49 y paso 11 |
| R-17 `Ctrl+C` repetidos | UC-05 A6 | T49 (Linux ✔) y paso 7 f |

### 8.1 Trazabilidad por requisito no funcional

Para los casos de uso, la trazabilidad está en las tablas anteriores (escenario → tareas → implementación → pruebas → pendiente en Windows) y en el [modelo de casos de uso, §4](../requirements/use-case-model.md#4-trazabilidad-con-el-diseño) (componentes y módulos). Esta tabla añade los requisitos de la [especificación complementaria](../requirements/supplementary-specification.md); su fuente es esa especificación, y su criterio, el texto del requisito.

| ID | Componentes y código | Tareas | Pruebas (evidencia) | Verificable en Linux | Necesita Windows | Divergencias y estado |
|---|---|---|---|---|---|---|
| SUP-F01 Salida en inglés | `command_line` | E1 | Pruebas de los comandos (Linux ✔) | Sí | Consola (paso 12) | — |
| SUP-F02 Códigos de salida | `command_line/exit_code.py`, `command_parser.py` | E1, T39, T49 | Linux ✔ | Sí | Paso 3 y 7 | **Divergencia documentada:** se añadió `130` (interrupción) y `1` por cola ocupada o base de datos inutilizable en todos los comandos; actualizado en el diseño, §4.1 |
| SUP-F03 Precedencia de la configuración | `configuration/settings_loader.py` | E1 | Linux ✔ | Sí | — | — |
| SUP-U01 Mensajes con la acción | Todos | E1, T49 | Linux ✔ (LFS, configuración, cola ocupada, nombre final) | Sí | Paso 2 | — |
| SUP-U02 Progreso limitado | `media_extraction/progress_event_translator.py` | E1 | Linux ✔ | Sí | — | — |
| SUP-U03 Instalación en cuatro comandos | README | E1 | Windows E1 ✔ | No | Paso 1 | — |
| SUP-R01 Cierre sin perder jobs | `job_queue/recover_interrupted_jobs.py`, `media_extraction` | T31, T32, T35, T44 | Linux ✔ (§5.1 automatizado) | Sí, en parte | Pasos 7, 8 (obligatorio) | — |
| SUP-R02 Sin procesos huérfanos | `workers/*process_tree_terminator.py` | T33–T35 | Linux ✔ (grupos de procesos); `windows` ⏳ (Job Object) | Solo POSIX | Pasos 3, 4, 6, 7, 8 | Mitigado (Linux) |
| SUP-R03 Un fallo no detiene la cola | `job_queue/run_queue.py` | E1 | Linux ✔ | Sí | — | — |
| SUP-R04 Worker caído detectado y sustituido | `workers/process_worker_pool.py` | E1, T35 | Linux ✔ | Sí | Paso 5 | — |
| SUP-R05 Sin descargas duplicadas | `job_storage` (índice), `job_queue` | E1, T28, T49 | Linux ✔ (también reintento de playlist) | Sí | Paso 5.1, 5.2 | — |
| SUP-P01 1 worker por defecto | `configuration` | E1 | Linux ✔ | Sí | — | — |
| SUP-P02 Memoria del worker no crece con la playlist | `media_extraction/yt_dlp_expansion.py` | T25–T27 | Linux ✔ (servidor local); `network` no ejecutable aquí | En parte | Paso 13 | Abierto (R-06) |
| SUP-P03 Progreso fuera de la base de datos | `job_queue/job_event_applier.py` | E1 | Linux ✔ | Sí | — | — |
| SUP-P04 Presupuesto de memoria | — | E1 (trasladado) | Ninguna | No | Paso 13 | **Pendiente:** se fija con la medición de la campaña |
| SUP-S01 Actualización de yt-dlp documentada | ADR-0002 | E1 | Pruebas de contrato (Linux ✔) | Sí | — | — |
| SUP-S02 Reglas de importación, formato, linter y tipos | Todo el código | Continuo | `scripts/run_checks.py` (Linux ✔) | Sí | Paso 3 | — |
| SUP-S03 Inglés en identificadores, español en docstrings | Todo el código | Continuo | Revisión | Sí | — | — |
| SUP-S04 Reglas de la cola sin yt-dlp, SQLite ni procesos | `jobs`, `job_queue` | Continuo | `lint-imports` y dobles (Linux ✔) | Sí | — | — |
| SUP-C01 Windows 10/11 x64, Python ≥3.11 con uv | `pyproject.toml` | E1 | Windows E1 ✔ | No | Paso 1 | — |
| SUP-C02 yt-dlp 2026.10.26 solo en `yt_dlp_*` | `media_extraction` | E1 | `lint-imports` (Linux ✔) | Sí | — | — |
| SUP-C03 ffmpeg 9.0 LGPL incluido con LFS | `vendor/ffmpeg/` | E1 | `windows` ⏳ (`tests/vendor/`) | No | Pasos 1–3 | — |
| SUP-C04 Solo `run` cambia estados | `job_queue`, `command_line` | E1, T36, T45 | Linux ✔ | Sí | — | — |
| SUP-C05 Sin CI | Proceso | — | — | — | — | — |
| SUP-L01–L03 Licencias | `LICENSE`, `vendor/ffmpeg/` | E1 | Revisión | Sí | — | — |

### 8.2 Clasificación de las pruebas (2026-11-26, `main` tras la actualización de yt-dlp)

568 pruebas recogidas:

| Clase | Número | Estado |
|---|---|---|
| `PASSED` (satisfactorias) | 554 | Ejecutadas y pasadas en el entorno de desarrollo (`scripts/run_checks.py`), todas las que no requieren Windows ni red |
| `FAILED_PRODUCT_DEFECT` (fallidas por defectos del producto) | 0 | — |
| `WINDOWS_PENDING` en Linux; pasadas en Windows | 10 (16 seleccionadas en Windows) | 4 del terminador (Job Object), 3 de la build de ffmpeg, 3 de reclamaciones de nombres finales; en Windows se seleccionan además las 6 del terminador de la plataforma. **Pasaron en Windows** sobre `5f30151` y sobre `f3e041a`. Siguen pendientes de validación real SUP-P04 y los pasos manuales 5.2 a 13 |
| `BLOCKED_BY_ENVIRONMENT` (bloqueadas por el ambiente) | 4 | Las pruebas `network` (3 de expansión de YouTube y la regresión de T42-D3): el proxy del entorno de desarrollo responde HTTP 403. En Windows, sobre `f3e041a` (yt-dlp 2026.11.23), **pasaron las 4** |
| `SKIPPED_JUSTIFIED` (omitidas justificadamente) | 0 en Linux; 7 en Windows | En Windows se omiten por diseño 4 de `Ctrl+C` con señales POSIX (equivalente: paso 7), 2 del localizador de ffmpeg con un script POSIX y 1 de nombres que distinguen mayúsculas (equivalente: pruebas `windows` de reclamaciones) |

### 8.3 Verificación de desarrollo

`uv run python scripts/run_checks.py` sobre el `main` publicado: formato, linter, tipos (también de `scripts/`), reglas de importación y pruebas pasan (código 0 en cada una; 554 pruebas). La sesión de pruebas no detectó cambios en los datos reales del usuario. La evidencia de Windows y su vigencia están en el [registro de resultados](t42-results.md).
