# ADR-0013: Abstracción `ProcessTreeTerminator`

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Resuelve:** el pendiente de [ADR-0008](adr-0008-process-based-worker-pool.md) (Job Object o `psutil`)

## Contexto

Al terminar un worker a la fuerza, en Windows sus procesos hijos (ffmpeg, deno) siguen vivos. El análisis planteó elegir entre un Job Object de Windows (vía `ctypes`) y `psutil`. Plantearlo así era un error de diseño: elegía una **implementación** donde hacía falta una **abstracción**.

## Decisión

`ProcessWorkerPool` depende de una interfaz, no de un mecanismo del sistema operativo:

```python
class ProcessTreeTerminator(Protocol):
    """Termina un proceso raíz junto con todos los procesos que este cree."""

    def register_root_process(self, process_id: int) -> None:
        """Registra el proceso cuyo árbol completo se terminará."""

    def terminate_tree(self) -> None:
        """Termina el proceso raíz registrado y todos sus descendientes."""
```

- **Ubicación:** `job_execution/process_tree_terminator.py`. Es una abstracción interna del plugin de ejecución: `use_cases/` y `download_queue/` no saben que existen procesos.
- **Inyección:** `ProcessWorkerPool` recibe una fábrica (`Callable[[], ProcessTreeTerminator]`) y crea un terminador por worker. `composition_root.py` decide la implementación.
- **Primera y única implementación:** `WindowsProcessTreeTerminator`, que usa un Job Object con `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` vía `ctypes`.
  - Windows garantiza que no queden procesos huérfanos aunque el proceso principal muera.
  - No añade dependencias.
- **Nombre:** el término *Job Object* no aparece en nombres propios. En el proyecto, *job* significa un job de la cola ([vocabulario](../design/00-vocabulary.md)); usarlo para un mecanismo del sistema operativo sería desinformación (principios de nombres #2 y #8).

Principios aplicados:
- **Inversión de dependencias:** el pool depende de la abstracción.
- **Abierto/cerrado:** soportar otra plataforma es añadir una implementación sin modificar el pool.
- **Segregación de interfaces:** dos operaciones, las únicas que el pool necesita.
- **YAGNI:** una sola implementación mientras solo se soporte Windows ([ADR-0004](adr-0004-windows-x64-target-platform.md)).

## Consecuencias

- La terminación forzada se prueba con `FakeProcessTreeTerminator`, sin procesos reales.
- `WindowsProcessTreeTerminator` tiene sus propias pruebas de integración, marcadas como `windows`.
- Si se soporta Linux o macOS, se añade una implementación (por ejemplo, con grupos de procesos POSIX o `psutil`) y se elige en `composition_root.py`.
