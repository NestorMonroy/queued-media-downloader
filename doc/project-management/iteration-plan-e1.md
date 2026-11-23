# Plan de iteración E1: esqueleto ejecutable

- **Fase RUP:** Elaboración
- **Iteración:** E1 de 2 (la Elaboración se acortó al pasar UC-04 a E2)
- **Inicio:** al crear el repositorio (T01)
- **Duración:** delimitada por alcance: la iteración se cierra cuando T19 confirma los criterios de la sección 5 ([caso de desarrollo, §5](../process/development-case.md#5-roles-y-duración-de-las-iteraciones))
- **Estado:** cerrada el 2026-11-23, con el criterio 6 trasladado a E2 (enfoque híbrido, [ADR-0022](../notes/adr-0022-hybrid-approach-and-task-decomposition.md))

---

## 1. Objetivo

Demostrar la arquitectura de extremo a extremo con el escenario más simple: **instalar, encolar y descargar un solo video en Windows**, recorriendo todos los componentes con implementaciones reales (pool de procesos, SQLite, yt-dlp y ffmpeg incluido).

## 2. Alcance

| Caso de uso | Escenarios incluidos | Escenarios excluidos |
|---|---|---|
| [UC-01](../requirements/use-cases/uc-01-install-and-verify-environment.md) | Flujo básico; A1 (puntero de Git LFS); A6 (configuración no válida) | A4 (`PATH`), A5 (hash contra `SOURCE.md`) |
| [UC-02](../requirements/use-cases/uc-02-enqueue-media.md) | Flujo básico; A1 (URL no válida) | A3 (bloqueo de la base de datos) |
| [UC-03](../requirements/use-cases/uc-03-download-single-media.md) | Flujo básico (incluida la unión con ffmpeg); A2 (fallo clasificado) | A1, A3 a A6 (pasan a E2) |

Fuera de E1: cancelación (UC-05), recuperación y reanudación (UC-06), playlists (UC-04) y los comandos `retry`, `list`, `show` y `purge`.

## 3. Riesgos que neutraliza

| Riesgo | Cómo se comprueba en E1 |
|---|---|
| R-01 Pool de procesos con *spawn* | Pruebas del pool con `get_context("spawn")` + descarga real en Windows |
| R-02 Consumo de memoria | Medición de RSS máxima en Windows durante una descarga con unión por ffmpeg |
| R-03 Binarios de ffmpeg incluidos | Prueba `windows` de arranque de `ffmpeg.exe` y `ffprobe.exe` desde `vendor/` |
| R-12 Licencias (LGPL de ffmpeg) | `LICENSE.txt` y `SOURCE.md` en `vendor/ffmpeg/` |

## 4. Trabajo

### 4.1 Cómo se descompone

La iteración se descompone en cuatro niveles ([caso de desarrollo, §4](../process/development-case.md#4-descomposición-del-trabajo)):

```text
Fase           Elaboración
└─ Iteración   E1: esqueleto ejecutable (elegida por riesgo: R-01, R-02, R-03, R-12)
   └─ Slice    Incremento ejecutable de extremo a extremo (un escenario de caso de uso)
      └─ Tarea Un cambio en un componente con TDD: prueba primero, un PR revisable de una sentada
```

Cada slice termina en algo que se ejecuta. Cada tarea termina cuando pasa la prueba indicada y cumple la [definición de terminado](../process/development-case.md#definición-de-terminado-por-cambio). El avance se mide en tareas terminadas sobre 23 (T05 se eliminó: [ADR-0025](../notes/adr-0025-reference-material-distribution.md); T20 y T21 se añadieron tras las revisiones de T15 y T17; T22, T23 y T24, tras la primera ejecución de T19).

Roles ([caso de desarrollo, §5](../process/development-case.md#roles)): **Responsable** del proyecto, **Agente** de implementación y **Evaluador** en Windows. Toda tarea del Agente termina con un *pull request*: las pruebas y las herramientas verifican el código, y el Responsable revisa que las pruebas expresen el criterio de terminado antes de integrar ([ADR-0024](../notes/adr-0024-verification-by-tdd-and-review-focus.md)).

### 4.2 Slice 0: entorno

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T01 | Repositorio en GitHub y Git LFS para `vendor/ffmpeg/` | Responsable | `git lfs track` muestra solo `vendor/ffmpeg/**` | — |
| T02 | `pyproject.toml` (`uv_build` con `module-root = ""`, `yt-dlp[default,deno]==2026.10.26`, `[tool.uv] environments`, grupo `dev`, Ruff, mypy estricto, marcadores de pytest), `uv.lock` y esqueleto de componentes con su `__init__.py` | Agente | Las cinco comprobaciones locales pasan con el proyecto vacío | T01 |
| T03 | Contratos de import-linter: un `protected` por componente y `forbidden` para `yt_dlp` (el contrato `layers` se adelantó a T02, porque `lint-imports` no se ejecuta sin contratos) | Agente | `lint-imports` pasa; un import prohibido de prueba lo rompe | T02 |
| T04 | Build de ffmpeg ([ADR-0018](../notes/adr-0018-ffmpeg-build-selection.md)) con `LICENSE.txt` y `SOURCE.md` (URL con fecha, SHA-256, enlace al código fuente) | Agente | El SHA-256 coincide; la prueba `windows` de arranque está escrita | T01 |

### 4.3 Slice A: encolar (UC-02)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T06 | `jobs/`: `Job`, `JobKind`, `JobStatus`, `MediaKey`, `DownloadOptions`, `FailureReason` y `job_lifecycle` | Agente | Prueba de la tabla completa de transiciones, permitidas y rechazadas | T02 |
| T07 | `job_storage/`: contratos, `SqliteJobStore`, migración `0001_create_jobs.sql` y PRAGMAs | Agente | Pruebas de integración sobre SQLite real, incluido el índice de duplicados | T06 |
| T08 | `configuration/`: `Settings` y carga con su orden de prioridad | Agente | Pruebas de prioridad entre argumentos, entorno, `config.toml` y valores por defecto | T02 |
| T09 | `job_queue/enqueue_media.py`, comando `enqueue` y `composition_root` mínimo (abre el job store; se autoriza en los contratos `protected`) | Agente | `enqueue URL` crea un job `EXPANSION` `PENDING`; una URL no válida no crea ninguno | T07, T08 |

### 4.4 Slice B: descargar sin unir (UC-03, servidor HTTP local)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T10 | `jobs/job_events.py` (los job events de UC-03) | Agente | Prueba de serialización entre procesos | T06 |
| T11 | `media_extraction/`: contrato `MediaSource`, `expand` para contenido único y `yt_dlp_parameters` | Agente | Prueba contra el servidor HTTP local: publica `SingleMediaFound` | T10 |
| T12 | `media_extraction/`: `download`, `SelectedFormatRecorder`, `FinalPathRecorder`, `progress_event_translator` y `failure_classifier` | Agente | Pruebas de contrato con las excepciones reales de yt-dlp; descarga contra el servidor local | T11 |
| T13 | `workers/`: contrato `WorkerPool`, `ProcessWorkerPool` y `worker_loop` (`RunJob`, `ShutDown`; sin cancelación ni reciclado) | Agente | Pruebas con `get_context("spawn")` y `FakeMediaSource` | T10, T11 |
| T14 | `job_queue/`: `RunQueue` (sin job requests) y `JobEventApplier` | Agente | Pruebas con `ScriptedWorkerPool` e `InMemoryJobStore` | T07, T13 |
| T15 | Comando `run`, `composition_root` completo (creado en T09) y presentación del progreso | Agente | `enqueue` + `run` descargan un archivo del servidor local y el job queda `COMPLETED` | T09, T12, T14 |

### 4.5 Slice C: descargar uniendo con ffmpeg (UC-03 completo)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T16 | `ffmpeg_discovery/`: localización (configurada y `vendor/`), verificación con `-version`, punteros de Git LFS y caché del hash | Agente | Pruebas con archivos ficticios | T04 |
| T17 | Verificación de ffmpeg al arrancar `run` (UC-03, paso 2), descarga de extremo a extremo con unión de audio y video, y efecto de `--audio-only` (extracción del audio, que requiere ffmpeg) | Agente | Un video y un audio generados con ffmpeg se descargan del servidor local y se unen en un solo archivo; con `--audio-only` queda solo el audio | T15, T16 |

### 4.6 Slice D: diagnosticar (UC-01)

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T18 | `diagnostics/` y comando `diagnose` | Agente | Informa de ffmpeg, ffprobe, deno y la base de datos; códigos de salida `0` y `2` correctos | T07, T16 |

### 4.7 Cierre

| ID | Tarea | Rol | Terminada cuando | Depende de |
|---|---|---|---|---|
| T21 | La regla de duplicados distingue el tipo de archivo: mismo contenido con y sin `--audio-only` son dos descargas ([ADR-0012](../notes/adr-0012-no-download-archive-no-database-triggers.md), migración `0002`) | Agente | El mismo contenido se descarga como video y como audio; dos descargas del mismo tipo siguen quedando `SKIPPED`; la migración conserva los datos | T17 |
| T20 | Configurar `logging` hacia un archivo en `state/logs/` (en la consola solo queda la presentación) y ocultar los pasos internos de yt-dlp, como `MoveFiles` | Agente | Un job fallido muestra su error una sola vez en la consola y completo en el log; `MoveFiles` no aparece | T15 |
| T22 | Aserciones de prueba portables: la evaluación en Windows mostró dos pruebas que asumían Linux (rutas con `/` y ffmpeg del `PATH`) | Agente | `uv run pytest` pasa en Windows | T19 (primera ejecución) |
| T23 | Los jobs de solo audio descargan en la subcarpeta `audio`: su descarga intermedia podía llamarse como el video unido de otro job, que yt-dlp reutilizaba y `ExtractAudio` borraba (hallado en T19) | Agente | Un DASH en WebM descargado como video y como audio deja los dos archivos | T19 (paso 7) |
| T24 | yt-dlp sin secuencias de terminal (`color="never"`): en Windows coloreaba `ERROR:` y el prefijo llegaba al mensaje del job y al log (hallado en T19) | Agente | Un error de yt-dlp con terminal de color llega al job sin códigos ANSI ni prefijo | T19 (paso 9) |
| T19 | Evaluación en Windows: `pytest -m windows`, flujo desde un clon nuevo, descarga real de YouTube, comprobación de procesos y medición de memoria | Evaluador | Los criterios de la sección 5 cumplidos; SUP-P04 fijado; lista de riesgos actualizada | Todas |

### 4.8 Camino crítico

```text
T01 → T02 → T06 → T07 → T14 → T15 → T17 → T19
```

T03, T04, T08, T10 a T13 y T16 pueden avanzar en paralelo con el camino crítico. A partir de T15 ya hay una descarga real de extremo a extremo: si el pool con *spawn* (R-01) falla, se descubre a mitad de la iteración, no al final.

---

## 5. Criterios de evaluación

La iteración se considera cumplida si:

1. Las cinco comprobaciones locales pasan ([caso de desarrollo, §3](../process/development-case.md#comprobaciones-locales-antes-de-integrar-en-main)).
2. `uv run pytest -m windows` pasa en el entorno Windows.
3. En Windows, desde un clon nuevo: `uv sync`, `diagnose`, `enqueue` y `run` descargan un video que requiere unir audio y video, y termina con código `0`.
4. Descarga real manual de un video de YouTube en Windows (con deno).
5. Al terminar `run` no queda ningún proceso de ffmpeg ni deno.
6. La memoria máxima (RSS) del proceso principal, del worker y de ffmpeg está medida, y SUP-P04 queda fijado.

## 6. Evaluación

Guion para el Evaluador: [evaluation-guide-e1.md](evaluation-guide-e1.md).

**Evaluada el 2026-11-23** en un equipo físico con Windows 11 x64, CPython 3.12.13 (descargado por uv) y uv 0.11.8, desde un clon nuevo de GitHub.

### 6.1 Resultado por criterio

| Criterio | Resultado | Evidencia |
|---|---|---|
| 1. Cinco comprobaciones | Cumplido | 287 pruebas pasan y 2 se omiten (scripts POSIX), tras T22 |
| 2. `pytest -m windows` | Cumplido | 3 de 3 |
| 3. Clon nuevo, `uv sync`, `diagnose`, `enqueue` y `run` con unión | Cumplido | `diagnose` con la build incluida y el deno del entorno; unión `395+251` en `.webm` con video y audio |
| 4. Descarga real de YouTube con deno | Cumplido | "Me at the zoo" como video, como solo audio (`audio\….opus`) y como duplicado `SKIPPED` |
| 5. Sin procesos al terminar | Cumplido | Sin ffmpeg, deno ni workers tras `run` |
| 6. Memoria máxima y SUP-P04 | **Abierto, pasa a E2** | El script del guion necesitó una corrección (lanzador del entorno virtual frente al Python real); la medición se repite en la evaluación de E2 |

Pasos adicionales: el fallo controlado (paso 9) termina con código `1`, un mensaje de una línea y el error completo en el log; una playlist termina en `UNSUPPORTED_URL` sin afectar al resto de la cola.

### 6.2 Hallazgos

| Hallazgo | Tipo | Resolución |
|---|---|---|
| Smart App Control bloquea `uv.exe` y la build de ffmpeg, sin firmar | Entorno | [ADR-0026](../notes/adr-0026-smart-app-control-precondition.md): precondición documentada; riesgo R-13 |
| Dos pruebas asumían Linux (rutas con `/`, ffmpeg del `PATH`) | Pruebas | T22 |
| Un job de solo audio reutilizó y borró el video unido de otro job | **Defecto con pérdida de datos** | T23: subcarpeta `audio` |
| Un archivo ya descargado se mostraba al 0,0 % | Presentación | T23 (commit aparte) |
| yt-dlp coloreaba `ERROR:` y el prefijo llegaba al mensaje y al log | Defecto | T24: `color="never"` |
| El guion esperaba `.mp4` y `.m4a`, y el script de memoria medía los lanzadores | Guion | Corregido en el guion |

### 6.3 Riesgos

R-01 (pool con *spawn*) y R-03 (ffmpeg incluido) quedan mitigados con evidencia en Windows. R-12 (LGPL) queda mitigado con `LICENSE.txt` y `SOURCE.md`. R-02 (memoria) sigue abierto y pasa a E2. Se añade R-13 (Smart App Control).
