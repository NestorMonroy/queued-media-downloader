# ADR-0029: Implementación de `ProcessTreeTerminator` (D1)

- **Estado:** Aceptada (D1 aprobada por el Responsable el 2026-11-25)
- **Fecha:** 2026-11-25

| Aspecto | Estado |
|---|---|
| Decisión de arquitectura | **APROBADA**: Job Object por worker en Windows; grupos de procesos en POSIX |
| Implementación en Windows | **Hecha** (T34: terminadores; T35: integración en el pool) |
| Validación en ejecución sobre Windows | **PENDIENTE**: experimento de T33 y pruebas `windows`, en la campaña final ([plan de E2, §7](../project-management/iteration-plan-e2.md#7-campaña-final-de-validación-en-windows)) |
| Aceptación final | **PENDIENTE**: depende de los resultados reales de la campaña final |

Aprobar D1 autoriza la implementación. No es evidencia de que funcione en Windows: los resultados de Linux de este ADR describen Linux, no Windows.
- **Tarea:** T33 del [plan de E2](../project-management/iteration-plan-e2.md#44-slice-c-terminar-el-árbol-de-procesos-adr-0013)
- **Concreta:** [ADR-0013](adr-0013-process-tree-terminator-abstraction.md) (contrato) y [ADR-0008](adr-0008-process-based-worker-pool.md) (pool de procesos)
- **Experimento:** [T33: terminar el árbol de procesos](experiments/t33-process-tree-termination.md)

## Contexto

ADR-0013 fijó el contrato `ProcessTreeTerminator` y anticipó un Job Object como implementación para Windows, pero el plan de E2 dejó la implementación abierta como D1. Este ADR la analiza contra lo que el código hace realmente, con evidencia experimental, y propone una decisión.

Se distinguen tres situaciones que no deben confundirse:

| Situación | Ejemplo | Estado del job | Archivos parciales |
|---|---|---|---|
| **Cancelación definitiva** | `cancel JOB_ID` (UC-05) | `CANCELLED` | Se conservan para un posible reintento (UC-05, postcondición) |
| **Interrupción recuperable** | Corte de luz, cierre de la terminal, `run` terminado a la fuerza, `Ctrl+C` | Queda `RUNNING`; el siguiente `run` lo recupera a `PENDING` (T31) | Se conservan; la reanudación los continúa (T32) |
| **Terminación controlada** | Fin de `run`, worker que no responde al apagado, worker caído | Sin cambios si el worker estaba libre; `FAILED` (`WORKER_CRASHED`) si cayó con un job | Se conservan |

En las tres, terminar el árbol de procesos debe hacer lo mismo: que no quede ningún proceso del worker. Lo que cambia es el estado que escribe el proceso principal, no el mecanismo.

## 1. Inventario de la arquitectura de procesos

Verificado en el código del proyecto, en yt-dlp 2026.10.26 y en la biblioteca estándar de Python 3.13.

| Pieza | Quién la crea y cómo | Evidencia |
|---|---|---|
| Proceso principal | `uv run` → intérprete del venv | — |
| Worker | `ProcessWorkerPool._start_worker`: `multiprocessing.get_context("spawn").Process(daemon=True)` | `workers/process_worker_pool.py` |
| Worker en Windows | `_winapi.CreateProcess(python_exe, cmd, None, None, False, 0, env, …)`: flags `0`, sin grupo de procesos ni consola propios. En un venv lanza directamente el intérprete base, sin el lanzador (bpo-35797), así que el PID del worker es el del intérprete real | `multiprocessing/popen_spawn_win32.py:64-78` |
| yt-dlp | Se ejecuta **dentro** del worker, como biblioteca (`YoutubeDL` en `media_extraction/`) | ADR-0002 |
| ffmpeg y ffprobe | yt-dlp los lanza desde el worker con `yt_dlp.utils.Popen` (`subprocess.Popen` con `STARTUPINFO`, sin `creationflags`): al unir formatos, extraer el audio y consultar versiones | `yt_dlp/utils/_utils.py:838-895`, `postprocessor/ffmpeg.py:356` |
| deno | yt-dlp lo lanza desde el worker con el mismo `Popen` para resolver los retos de YouTube durante la extracción | `extractor/youtube/jsc/_builtin/deno.py:104` |
| Nietos | ffmpeg y deno no lanzan procesos en el uso que hace yt-dlp | — |

Consecuencias del inventario:

- **Herencia:** ffmpeg y deno se crean sin `CREATE_BREAKAWAY_FROM_JOB` ni `CREATE_NEW_PROCESS_GROUP`. En Windows heredan el Job Object del worker, si lo tiene; en POSIX heredan su grupo de procesos.
- **Identificación por job:** hoy no existe. El pool sabe qué job tiene cada worker (`WorkerHandle.assigned_job_id`), y un worker ejecuta un solo job a la vez. Identificar el árbol del worker identifica, por tanto, los procesos del job.
- **Handles:** `multiprocessing` guarda un handle del worker (`Popen._handle`). Mientras está abierto, Windows no reutiliza su PID.

## 2. Flujo real de creación y terminación (antes de D1)

| Momento | Qué hace hoy el código | Qué les pasa a ffmpeg y deno |
|---|---|---|
| Arranque | `process.start()`; nada se registra | — |
| Job en curso | yt-dlp lanza y espera ffmpeg o deno (`communicate_or_kill`) | Hijos del worker |
| yt-dlp recibe una excepción | `communicate_or_kill` mata a su hijo (`except BaseException`) | Terminan |
| `shut_down`: el worker no sale en 10 s | `process.kill()`: `TerminateProcess` solo al worker | **Siguen vivos** |
| Worker caído | `_replace_crashed_workers` lo sustituye y falla el job | **Siguen vivos** y siguen escribiendo |
| `run` termina con normalidad | `daemon=True`: `multiprocessing` llama a `terminate()` de cada worker al salir | **Siguen vivos** si el worker estaba en un job |
| `run` muere a la fuerza | Nada | **Siguen vivos**, y los workers también |
| Cancelación (UC-05) | No implementada (slice D) | — |

## 3. Hallazgos y limitaciones

1. **Huérfanos que siguen escribiendo (defecto actual).** Cuando un worker cae o se mata, `multiprocessing` solo termina el worker. El experimento lo mide: tras terminar el worker, su descendiente siguió escribiendo y el parcial pasó de 8 KiB a 408 KiB. Un ffmpeg huérfano puede seguir escribiendo el `.temp` de una unión mientras un reintento del mismo job escribe el mismo archivo.
2. **Si `run` muere, los workers también quedan vivos.** `daemon=True` solo actúa en una salida ordenada del proceso principal.
3. **Orden de registro.** Un Job Object solo contiene los procesos creados **después** de asignar el worker. El worker solo lanza procesos al recibir un `RunJob`, y el pool envía el primero después de arrancarlo: basta con registrar el worker antes del primer `submit`. El escenario de asignación tardía del experimento lo comprueba en Windows.
4. **`Ctrl+C` llega a todo el grupo de consola.** Worker, ffmpeg y deno comparten la consola y su grupo de procesos, así que `Ctrl+C` les llega a todos, no solo al proceso principal. El worker recibe `KeyboardInterrupt`, que no captura `_run_job` (`except Exception`), y ffmpeg se detiene por su cuenta. Esto no depende de D1, pero afecta a UC-05 A6: lo resuelve el slice D, por ejemplo haciendo que el worker ignore `Ctrl+C` con `SetConsoleCtrlHandler(NULL, TRUE)`, que Windows hereda en los hijos. Debe verificarse en T39 o T40.
5. **ADR-0013 está desactualizado en dos puntos.** Sitúa el contrato en `job_execution/` (el componente es `workers/`), y su contrato no tiene forma de liberar el mecanismo cuando un worker se sustituye.
6. **Cancelación cooperativa.** El worker solo lee instrucciones entre jobs, así que hoy no podría recibir una cancelación a mitad de una descarga. La terminación forzada no sustituye a la cooperativa: es su respaldo (UC-05 A2). Corresponde al slice D.

## 4. Alternativas

### 4.1 Job Object de Windows (`ctypes`)

`CreateJobObjectW` + `SetInformationJobObject` con `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; `AssignProcessToJobObject` con el handle del worker; `TerminateJobObject` para terminar el árbol. Windows mete en el Job Object todo proceso que el worker cree después.

### 4.2 Grupos de procesos

- **POSIX:** el worker se pone en su propio grupo (`os.setpgid(0, 0)` al arrancar, antes del primer job) y se termina con `os.killpg(pgid, SIGKILL)`.
- **Windows:** `CREATE_NEW_PROCESS_GROUP` solo sirve para dirigir `CTRL_BREAK_EVENT` a un grupo de consola, no para terminar procesos, y `multiprocessing` no permite pasar `creationflags` al crear el worker. No es una alternativa para terminar un árbol en Windows.

### 4.3 `taskkill /T /F /PID`

Lanza `taskkill.exe`, que toma una instantánea de los procesos y termina los que tienen como padre, directo o indirecto, el PID indicado.

### 4.4 `psutil`

`psutil.Process(pid).children(recursive=True)`, después `terminate()`/`kill()` y `wait_procs`. Es una dependencia nueva.

### 4.5 Cooperativa y después forzada

Pedir al worker que se detenga (bandera leída en el hook de progreso de yt-dlp, UC-05) y, si no confirma en `cancellation_grace_seconds`, terminar el árbol con uno de los mecanismos anteriores. No es una alternativa a 4.1–4.4, sino una forma de combinarlas; ya es el diseño de UC-05.

## 5. Matriz comparativa

| Criterio | 4.1 Job Object | 4.2 Grupo POSIX | 4.3 `taskkill /T` | 4.4 `psutil` |
|---|---|---|---|---|
| Funcionamiento | Contenedor del kernel; termina por pertenencia | Señal al grupo | Recorre el árbol por PID padre | Recorre el árbol por PID padre |
| Plataforma | Windows 8 o posterior (Job Objects anidados) | POSIX | Windows | Ambas |
| Dependencias nuevas | Ninguna (`ctypes`) | Ninguna | Ninguna (`taskkill.exe` del sistema) | `psutil`, binaria |
| Descendientes | Todos los creados tras la asignación, a cualquier profundidad | Todos los que no cambien de grupo | Los que conserven la cadena de PID padre | Igual que `taskkill` |
| Carreras | Ninguna al terminar; el registro debe ocurrir antes del primer job | Ninguna al terminar; el grupo debe crearse antes del primer job | Un proceso creado entre la instantánea y la terminación sobrevive | Igual que `taskkill` |
| Reutilización de PID | No aplica: opera sobre handles | No mientras el grupo tenga miembros; el worker sin recoger mantiene reservado su PID | **Sí**: si el worker murió y su PID se reutilizó, `/T` termina los descendientes de otro proceso | Mitigada con `create_time`, no eliminada |
| Worker caído | Sus descendientes siguen en el Job Object y se terminan | Se terminan si el grupo tiene miembros | **No los encuentra**: Windows no actualiza el PID padre de los huérfanos | No los encuentra |
| `run` muere | **Windows los termina** al cerrar el último handle (`KILL_ON_JOB_CLOSE`) | Sobreviven | Sobreviven | Sobreviven |
| Parciales recuperables | Se conservan (terminar no borra archivos) | Se conservan (medido) | Se conservan | Se conservan |
| Aislamiento entre jobs | Un Job Object por worker | Un grupo por worker (medido) | Por PID | Por PID |
| Liberación de recursos | Un handle por worker; cerrarlo termina lo que quede | Ninguno | Un proceso externo por llamada | Objetos `Process` |
| Pruebas automatizadas | Pruebas `windows` con procesos reales; contadores del propio Job Object (`ActiveProcesses`) | En cualquier POSIX | Pruebas `windows`; salida localizada según el idioma del sistema | En cualquier sistema |
| Complejidad | ~120 líneas de `ctypes` (estructuras y cinco llamadas) | ~20 líneas | ~15 líneas, más interpretar la salida | ~20 líneas |
| Riesgo R-13 (Smart App Control) | Ninguno: solo `kernel32` | — | Ninguno | `psutil` incluye un `.pyd` cuya firma habría que verificar |

## 6. Evidencia experimental

El [experimento](experiments/t33-process-tree-termination.md) reproduce la jerarquía real (worker `spawn` → hijo con `Popen` sin flags → nieto que escribe un parcial e ignora `SIGTERM`) y prueba cada estrategia en cinco escenarios.

**Linux (ejecutado el 2026-11-25):**
- `worker_kill_only`, lo que hace hoy el pool, deja vivos al hijo y al nieto en todos los escenarios, y el nieto sigue escribiendo.
- `process_group` termina el árbol completo, también el de un worker ya caído. Conserva el parcial entero, no afecta a otro árbol y admite terminaciones repetidas.
- Ninguna estrategia POSIX termina el árbol cuando el proceso principal muere.

**Windows: pendiente.** Por decisión del Responsable, el experimento se ejecuta en la campaña final de validación, cuando estén implementados todos los casos de uso. El documento del experimento recoge el resultado esperado de cada estrategia y el procedimiento. Si en la campaña `job_object` no da *ninguno vivo* en sus cuatro escenarios (el quinto, la asignación tardía, es un control que debe dejar vivos al hijo y al nieto), el defecto se corrige allí y D1 se revisa.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| El proceso principal ya está en un Job Object que prohíbe los Job Objects anidados (Windows 7) | Windows 8 o posterior permite anidarlos; el producto es Windows 10/11 (ADR-0004). La implementación comprueba el error de `AssignProcessToJobObject` y lo informa al arrancar |
| El worker lanza un proceso antes de quedar registrado | El registro forma parte de `_start_worker`, antes de devolver el worker al pool; ningún `RunJob` puede llegar antes. Escenario de asignación tardía en el experimento |
| Cerrar el handle del Job Object de un worker vivo lo termina (`KILL_ON_JOB_CLOSE`) | Solo se cierra al sustituir o apagar el worker; queda documentado en el contrato |
| Un huérfano de un worker caído escribe el mismo archivo que el reintento | El pool termina el árbol del worker caído antes de sustituirlo y de publicar `WORKER_CRASHED` |
| Errores de `ctypes` (estructuras mal declaradas en 64 bits) | Pruebas `windows` que consultan los contadores del propio Job Object |
| R-04 (lista de riesgos) | Es el riesgo que esta decisión neutraliza; se cierra en T42 con las pruebas `windows` |

## 8. Alternativa recomendada

**Un Job Object por worker con `KILL_ON_JOB_CLOSE` como `WindowsProcessTreeTerminator`, y grupos de procesos como implementación POSIX para ejecutar las pruebas del contrato en cualquier sistema.** Se combinan con la cancelación cooperativa del slice D (4.5): la terminación del árbol es el respaldo tras `cancellation_grace_seconds`.

Justificación:
- Es la única alternativa que cumple el requisito especial de UC-05: *la terminación forzada no deja procesos huérfanos aunque el proceso de `run` muera*. `taskkill` y `psutil` dependen de que alguien llame a algo; si `run` muere, nadie lo hace.
- Opera sobre handles: no hay reutilización de PID ni carreras al terminar.
- Termina también los descendientes de un worker ya caído, que `taskkill` y `psutil` no encuentran.
- No añade dependencias ni binarios sin firmar (R-13).
- La implementación POSIX no es una segunda implementación de producto: permite probar el pool con procesos reales en cualquier sistema, que es lo que pide T34. Su limitación (no muere con el proceso principal) no afecta al producto, que es solo para Windows (ADR-0004).

## 9. Propuesta de implementación (T34 y T35, tras aprobar D1)

1. **Contrato** en `workers/process_tree_terminator.py` (corrige la ubicación de ADR-0013):

   ```python
   class ProcessTreeTerminator(Protocol):
       def register_root_process(self, process_id: int) -> None: ...
       def terminate_tree(self) -> None: ...
       def release(self) -> None: ...
   ```

   `release()` es nuevo: libera el mecanismo cuando el worker se sustituye o se apaga. Con un Job Object, liberarlo termina lo que quede vivo en él. `terminate_tree()` es idempotente.
2. **`WindowsProcessTreeTerminator`** (`workers/windows_process_tree_terminator.py`): crea el Job Object en `__init__` y asigna el worker en `register_root_process` (`OpenProcess` con `PROCESS_SET_QUOTA | PROCESS_TERMINATE`; el handle de `multiprocessing` impide que el PID se reutilice entretanto). `terminate_tree` llama a `TerminateJobObject` y espera a que `ActiveProcesses` llegue a 0; `release` llama a `CloseHandle`.
3. **`PosixProcessTreeTerminator`**: `terminate_tree` llama a `os.killpg(pgid, SIGKILL)` mientras el grupo tenga miembros. El worker crea su grupo al arrancar (`worker_loop`, antes de leer la primera instrucción), porque un proceso padre no puede cambiar el grupo de un hijo que ya ejecutó `exec`.
4. **Inyección:** `ProcessWorkerPool` recibe una fábrica `Callable[[], ProcessTreeTerminator]`; `composition_root.py` elige la implementación según `sys.platform`.
5. **Uso en el pool:**
   - **Al arrancar un worker:** crear su terminador y registrarlo antes de devolver el worker.
   - **Worker caído:** terminar su árbol antes de sustituirlo, para que ningún huérfano siga escribiendo.
   - **Apagado:** terminar el árbol de los workers que no salgan a tiempo, en lugar de `process.kill()`. Liberar todos los terminadores al final.
   - **`terminate_worker_running(job_id)`** (T35): terminar el árbol, liberar el terminador y arrancar un worker de reemplazo.
6. **Estado:** el pool no cambia estados; publica lo que ocurrió y el proceso principal escribe `CANCELLED`, `FAILED` o nada, según la situación (tabla del contexto).

## 10. Estrategia de pruebas

| Nivel | Qué | Dónde |
|---|---|---|
| Unitarias | El pool llama al terminador al arrancar, ante una caída, en el apagado forzado y en `terminate_worker_running`; lo libera al sustituir el worker. Con `FakeProcessTreeTerminator` | Cualquier sistema |
| Integración | `PosixProcessTreeTerminator` termina worker, hijo y nieto; aísla dos árboles; termina los descendientes de un worker caído; terminar dos veces no falla | POSIX |
| Integración | `WindowsProcessTreeTerminator`: los mismos casos, más el proceso principal muerto (`KILL_ON_JOB_CLOSE`) y `ActiveProcesses` = 0 | `windows` |
| Integración | `ProcessWorkerPool` real: un worker que lanza un subproceso y cae no deja huérfanos | Cualquier sistema y `windows` |
| Extremo a extremo | El escenario obligatorio de la [§5.1 del plan](../project-management/iteration-plan-e2.md#51-criterio-obligatorio-de-integración-entre-los-slices-b-y-c): interrupción real, terminación del árbol, recuperación con `Range` | Cualquier sistema (T35) y Windows (T42) |
| Extremo a extremo | Cancelar mientras ffmpeg une archivos no deja procesos (UC-05) | `windows`, en T42 |

Las pruebas siguen los procesos por handle o `pidfd`, nunca por PID, y solo terminan los procesos que crean.

## 11. Criterios de aceptación de D1 y del slice C

1. El experimento ejecutado en Windows confirma *ninguno vivo* para `job_object` en sus cuatro escenarios, y el control de asignación tardía deja vivos al hijo y al nieto. **Resultado parcial (T42, `t42-candidate-1`, 2026-11-25):** los cuatro escenarios de `job_object` dieron *ninguno vivo*; el control y dos escenarios de las otras estrategias no se pudieron observar por un defecto del experimento (T42-D2). **Repetido con el experimento corregido (commit `f3e041a`, 2026-11-25): las 13 filas coinciden con lo esperado; criterio cumplido.**
2. Tras `terminate_tree`, no queda vivo ningún proceso creado por el worker, a cualquier profundidad.
3. Terminar el árbol de un worker no afecta a otro worker ni a sus descendientes.
4. Los descendientes de un worker caído se terminan antes de sustituirlo.
5. Si `run` muere a la fuerza, Windows termina todos los workers y sus descendientes.
6. Los archivos parciales quedan intactos tras una terminación, en las tres situaciones.
7. `terminate_tree` repetido no falla; `release` libera el handle.
8. El escenario de la §5.1 del plan pasa automatizado y en Windows.

## 12. Impacto sobre el slice B

- **Recuperación (T31):** sin cambios. Un job interrumpido porque `run` murió sigue `RUNNING` y se recupera; ahora, además, no queda ningún worker ni ffmpeg suyo escribiendo mientras el siguiente `run` lo reanuda.
- **Reanudación (T32):** terminar el árbol no borra ni trunca el `.part` (medido: parcial entero, sin bytes ajenos). El `.temp` de una unión interrumpida lo sobrescribe la siguiente unión. Las partes `.f<id>` ya terminadas se reutilizan.
- **Worker caído:** el job sigue quedando `FAILED` (`WORKER_CRASHED`) y se reintenta con `retry`; lo nuevo es que sus descendientes se terminan antes de que el reintento escriba los mismos archivos.

## Decisión (D1)

Aprobada por el Responsable el 2026-11-25:

> **`WindowsProcessTreeTerminator` con un Job Object por worker (`ctypes`, `KILL_ON_JOB_CLOSE`, `TerminateJobObject`), sin dependencias nuevas, y `PosixProcessTreeTerminator` con grupos de procesos para las pruebas en cualquier sistema.** El contrato de ADR-0013 se amplía con `release()` y se sitúa en `workers/`. El pool termina el árbol al cancelar a la fuerza, al detectar un worker caído y en el apagado forzado. La validación en Windows (criterio 1 y pruebas `windows`) se hace en la campaña final.

Alternativas descartadas: `psutil` (dependencia nueva; no cubre la muerte de `run`) o `taskkill /T` (sin dependencias; no cubre la muerte de `run` ni los workers caídos, y es sensible a la reutilización de PID).

## Seguimiento de T34 (2026-11-25)

- **Contrato** en `workers/process_tree_terminator.py`, con `release()` y `ProcessTreeTerminationError`, más `become_process_tree_root()`, que el worker llama al arrancar, antes de su primera instrucción.
- **Windows** (`workers/windows_process_tree_terminator.py`): un Job Object por terminador con `KILL_ON_JOB_CLOSE`, sin `BREAKAWAY_OK`; handle no heredable; `terminate_tree` llama a `TerminateJobObject` y espera a que `ActiveProcesses` llegue a 0 (10 s como máximo); los errores de `CreateJobObjectW`, `OpenProcess` y `AssignProcessToJobObject` se convierten en `ProcessTreeTerminationError`.
- **POSIX** (`workers/posix_process_tree_terminator.py`): `killpg` con `SIGKILL`. Si el worker aún no creó su grupo, termina solo al worker, a través de un `pidfd` cuando existe. Diferencias documentadas en el módulo: el árbol no muere con el proceso principal, y un descendiente podría salir del grupo con `setsid`.
- **Asociación al crear el proceso:** `multiprocessing` no permite `CREATE_SUSPENDED` ni `PROC_THREAD_ATTRIBUTE_JOB_LIST`. La asignación ocurre justo después de crear el worker, sin carrera, porque el worker no lanza procesos hasta su primer job.

| Prueba | Linux | Windows |
|---|---|---|
| Contrato: raíz, hijo y nieto terminados; parcial intacto; aislamiento entre árboles; descendientes de una raíz caída; terminar y liberar dos veces; raíz que aún no es raíz de su árbol | ✔ (6) | ⏳ las mismas 6, marcadas `windows` al ejecutarse en Windows |
| El árbol muere con su proceso dueño (`KILL_ON_JOB_CLOSE`) | — (POSIX no lo garantiza) | ⏳ |
| Un proceso registrado no puede salir con `CREATE_BREAKAWAY_FROM_JOB` | — | ⏳ |
| El handle del Job Object no es heredable | — | ⏳ |
| Registrar un proceso inexistente falla con `ProcessTreeTerminationError` | — | ⏳ |

## Seguimiento de T35 (2026-11-25)

`ProcessWorkerPool` recibe una fábrica de terminadores; `composition_root.create_process_tree_terminator` elige la implementación según la plataforma.

| Momento | Qué hace el pool |
|---|---|
| Arranque de un worker | Crea su terminador y lo registra antes de devolverlo: ningún job le llega antes. Si el registro falla, termina el worker (aún sin procesos propios), libera el terminador y propaga `ProcessTreeTerminationError`; si ocurre al crear el pool, apaga los workers ya arrancados |
| Worker caído | Termina su árbol **antes** de recoger sus últimos mensajes, publicar `WORKER_CRASHED` y arrancar el reemplazo |
| `terminate_worker_running(job_id)` | Termina el árbol del worker, recoge lo que llegó a enviar (sigue llegando por `collect_events`), libera el terminador y arranca un reemplazo. No publica nada en nombre del job |
| Apagado | Los workers que no salen en `SHUT_DOWN_TIMEOUT_SECONDS` se terminan con su árbol, no solo con `kill()`. Todos los terminadores se liberan |
| `terminate_tree` falla (Windows, plazo agotado) | Se registra el error y se termina al menos el worker con `kill()` |

Pruebas con procesos reales (Linux ✔; en la campaña, también en Windows): el hijo de un worker caído muere antes del reemplazo; `terminate_worker_running` termina el worker y su hijo y deja el pool listo; el apagado termina el árbol de un worker colgado; registro antes de cualquier job y liberación al final; un registro fallido no deja workers vivos; y el escenario obligatorio de la §5.1 del plan.

## Seguimiento de T49: `Ctrl+C` repetidos (2026-11-26)

Un tercer `Ctrl+C` volvía a lanzar `KeyboardInterrupt` en mitad de la terminación inmediata de los árboles, y uno posterior a restaurar el manejador mataba `run` con una traza: cualquiera de los dos podía dejar un worker vivo. Ahora, tras el segundo `Ctrl+C`, los siguientes se ignoran hasta que `run` sale; el manejador abarca también el arranque y el apagado del pool, y un `Ctrl+C` durante el apagado ordenado pasa a terminar cada árbol. Linux ✔ (`SIGINT` real); en Windows, donde `Ctrl+C` es un evento de consola, se valida en la campaña (paso 7, caso f).
