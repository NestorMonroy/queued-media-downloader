# Experimento de T33: terminar el árbol de procesos de un worker

- **Script:** [`scripts/experiments/process_tree_termination.py`](../../../scripts/experiments/process_tree_termination.py)
- **Decisión a la que sirve:** D1 ([ADR-0029](../adr-0029-process-tree-termination-on-windows.md))

## Qué reproduce

La jerarquía real del proyecto, verificada en el código ([ADR-0029, §1](../adr-0029-process-tree-termination-on-windows.md#1-inventario-de-la-arquitectura-de-procesos)):

```text
proceso principal (run)
└── worker            multiprocessing, contexto spawn, como ProcessWorkerPool
    └── hijo          subprocess.Popen sin creationflags, como yt-dlp lanza ffmpeg o deno
        └── nieto     escribe un archivo parcial sin parar e ignora SIGTERM
```

El nieto representa un descendiente de segundo nivel. ffmpeg y deno no lanzan procesos en el uso que hace yt-dlp, pero el contrato de [ADR-0013](../adr-0013-process-tree-terminator-abstraction.md) habla de *todos* los descendientes, y el nieto prueba que el mecanismo no depende de la profundidad.

El script solo termina procesos que creó. Los sigue por handle (`OpenProcess` en Windows, `pidfd` en Linux), no por PID: un PID reutilizado no puede llevarlo a otro proceso. Al terminar cada escenario termina lo que quede.

## Escenarios

| Escenario | Qué hace | Resultado esperado de una estrategia válida |
|---|---|---|
| `terminate_tree` | Termina el árbol mientras el nieto escribe; lo vuelve a terminar | Ningún proceso vivo; el parcial se conserva entero; la segunda terminación no falla |
| `isolation_other_tree_alive` | Dos árboles; termina uno | El otro árbol sigue vivo entero |
| `worker_crashed_then_terminate` | El worker muere solo (caída) y después se termina su árbol | Ningún proceso vivo: los descendientes de un worker caído también se terminan |
| `main_process_killed` | El proceso principal muere a la fuerza con un árbol en marcha | Ningún proceso vivo sin que nadie llame a nada (UC-05: *sin huérfanos aunque el proceso de `run` muera*) |
| `terminate_tree` con `job_object_assigned_late` (solo Windows) | Asigna el Job Object cuando el worker ya lanzó su hijo | El hijo y el nieto quedan fuera: demuestra que el registro debe ocurrir antes de enviar el primer job |

Estrategias: `worker_kill_only` (lo que hace hoy `ProcessWorkerPool`), `process_group` (POSIX), `taskkill_tree` y `job_object` (Windows).

## Cómo ejecutarlo

Desde la raíz del repositorio:

```powershell
uv run python scripts/experiments/process_tree_termination.py --json doc/notes/experiments/t33-windows-results.json
```

Tarda menos de un minuto. Escribe una tabla Markdown en la consola y, con `--json`, los datos completos. No necesita privilegios de administrador.

## Resultados en Linux (2026-11-25)

Linux 6.18, Python 3.13.18. Datos completos en [`t33-linux-results.json`](t33-linux-results.json).

| Escenario | Estrategia | Vivos después | Detalle |
|---|---|---|---|
| `terminate_tree` | `worker_kill_only` | hijo, nieto | El parcial pasó de 8 KiB a 408 KiB **después** de terminar el worker: los huérfanos siguen escribiendo |
| `isolation_other_tree_alive` | `worker_kill_only` | (el otro árbol, entero) | El árbol terminado dejó vivos hijo y nieto |
| `worker_crashed_then_terminate` | `worker_kill_only` | hijo, nieto | — |
| `main_process_killed` | `worker_kill_only` | worker, hijo, nieto | — |
| `terminate_tree` | `process_group` | ninguno | Parcial conservado (8 KiB) y entero; la segunda terminación no falla |
| `isolation_other_tree_alive` | `process_group` | (el otro árbol, entero) | El árbol terminado no dejó ninguno vivo |
| `worker_crashed_then_terminate` | `process_group` | ninguno | — |
| `main_process_killed` | `process_group` | worker, hijo, nieto | Un grupo de procesos no muere con el proceso principal |

Tras la ejecución no quedó ningún proceso del experimento.

## Resultados en Windows

**Primera ejecución: campaña T42, `t42-candidate-1`, 2026-11-25** (Windows 11 Home 10.0.26200, Python 3.12.13; JSON en [`t33-windows-results-candidate-1.json`](t33-windows-results-candidate-1.json)).

| Escenario | `worker_kill_only` | `taskkill_tree` | `job_object` |
|---|---|---|---|
| `terminate_tree` | hijo y nieto vivos (el parcial pasó de 12 288 a 417 792 bytes) ✔ | ninguno ✔ | **ninguno**, `job_active_processes` = 0 ✔ |
| `isolation_other_tree_alive` | otro árbol vivo ✔ | otro árbol vivo, objetivo sin procesos ✔ | otro árbol vivo, objetivo sin procesos ✔ |
| `worker_crashed_then_terminate` | `ERROR` (T42-D2) | `ERROR` (T42-D2) | **ninguno** ✔ |
| `main_process_killed` | `ERROR` (T42-D2) | `ERROR` (T42-D2) | **ninguno** ✔ |
| `terminate_tree`, asignación tardía | — | — | `ERROR` (T42-D2) |

Los `ERROR` son `PermissionError` al borrar la carpeta temporal: en Windows, `TerminateProcess` es asíncrono y la limpieza no esperaba a que los procesos que el escenario deja vivos a propósito soltaran el parcial. Es un defecto del experimento, no del producto (T42-D2); corregido en `269472e`, y el paso 4 se repite en la siguiente ejecución de la validación. Los cuatro escenarios de `job_object`, los que confirman D1, sí se observaron y dieron *ninguno vivo*.

**Segunda ejecución: commit `f3e041a`, 2026-11-25** (mismo equipo; JSON en [`t33-windows-results-f3e041a.json`](t33-windows-results-f3e041a.json)), con la limpieza corregida (T42-D2). Las 13 filas coinciden con el resultado esperado y ninguna es `ERROR`:

| Escenario | `worker_kill_only` | `taskkill_tree` | `job_object` |
|---|---|---|---|
| `terminate_tree` | hijo y nieto vivos ✔ | ninguno ✔ | **ninguno**, `job_active_processes` = 0 ✔ |
| `isolation_other_tree_alive` | otro árbol vivo ✔ | otro árbol vivo, objetivo sin procesos ✔ | otro árbol vivo, objetivo sin procesos ✔ |
| `worker_crashed_then_terminate` | hijo y nieto vivos ✔ | hijo y nieto vivos ✔ | **ninguno** ✔ |
| `main_process_killed` | todos vivos ✔ | todos vivos ✔ | **ninguno** ✔ |
| `terminate_tree`, asignación tardía | — | — | hijo y nieto vivos ✔ (el control) |

**Antes de la campaña: se ejecuta en la campaña final de validación en Windows** ([plan de E2, §7](../../project-management/iteration-plan-e2.md#7-campaña-final-de-validación-en-windows)). Los resultados de Linux no son evidencia para Windows. Pegar aquí la tabla que escribe el script y guardar el JSON junto a este documento. Lo que D1 necesita confirmar:

| Escenario | `worker_kill_only` | `taskkill_tree` | `job_object` |
|---|---|---|---|
| `terminate_tree` | Se espera: hijo y nieto vivos | Se espera: ninguno | Se espera: ninguno; `job_active_processes` = 0 |
| `isolation_other_tree_alive` | Otro árbol vivo | Otro árbol vivo | Otro árbol vivo |
| `worker_crashed_then_terminate` | Hijo y nieto vivos | Se espera: **hijo y nieto vivos** (el PID del worker ya no existe) | Se espera: ninguno |
| `main_process_killed` | Todos vivos | Todos vivos | Se espera: **ninguno** (`KILL_ON_JOB_CLOSE`) |
| `terminate_tree`, asignación tardía | — | — | Se espera: hijo y nieto vivos |
