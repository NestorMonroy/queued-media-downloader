# ADR-0008: Pool fijo de workers en procesos

- **Estado:** Aceptada (a validar en el prototipo)
- **Fecha:** 2026-11-22
- **Nota:** el pendiente sobre Job Object o `psutil` se resuelve en [ADR-0013](adr-0013-process-tree-terminator-abstraction.md); los términos vigentes están en [ADR-0014](adr-0014-use-case-structure-and-vocabulary.md).

## Contexto

La cola ejecuta varias descargas. Hallazgos en el código de yt-dlp 2026.10.26:
- `YoutubeDL` no documenta seguridad entre hilos y guarda estado mutable; `globals.py` tiene estado compartido por todo el proceso.
- No existe API de cancelación. Una excepción `DownloadCancelled` lanzada desde un hook de progreso sube hasta `download()`, pero solo funciona mientras se disparan hooks: no durante la extracción ni durante ffmpeg.
- Medición (`scripts/measure_footprint.py`): un proceso con yt-dlp cargado ocupa ~38 MB de RSS; el wheel incluye extractores perezosos.

En equipos modestos, el cuello de botella suele ser el ancho de banda y el disco, por lo que la concurrencia útil es de 1 a 2 descargas.

## Opciones consideradas

1. **Hilos:** ~38 MB en total; cancelación solo cooperativa; estado global compartido; un fallo afecta a toda la aplicación.
2. **Un proceso nuevo por trabajo:** aislamiento total, pero paga el arranque en cada trabajo.
3. **Pool fijo de procesos reutilizables:** aislamiento, cancelación inmediata y arranque pagado una vez; ~38 MB por worker.

## Decisión

**Pool fijo de procesos, 1 worker por defecto (configurable).**
- **Una instancia de `YoutubeDL` por trabajo**, nunca compartida.
- **Gestor propio** con `multiprocessing.Process`: `ProcessPoolExecutor` no permite cancelar una tarea en curso, y terminar uno de sus procesos rompe el pool entero (`BrokenProcessPool`).
- **Cancelación en dos niveles:** cooperativa (excepción desde el hook) y forzada (terminar el árbol de procesos del worker).
- **Árbol de procesos:** en Windows, ffmpeg y deno no mueren con el worker. Se usará un *Job Object* (ctypes) o `psutil`; pendiente de elegir.
- **Reciclado:** cada worker se reinicia tras N trabajos para limitar el estado acumulado.
- **Interfaz de worker** (enviar trabajo, cancelar, recibir eventos): el prototipo puede empezar con hilos y cambiar a procesos sin modificar la cola.

## Consecuencias

- Es la parte de mayor complejidad de implementación del proyecto.
- Los eventos de progreso viajan por una cola entre procesos: solo datos serializables (eventos propios, no el `info_dict` completo).
- Los hooks pueden llamarse desde hilos internos de yt-dlp (descarga concurrente de fragmentos): deben limitarse a publicar eventos.
- Solo el proceso principal escribe en SQLite ([ADR-0010](adr-0010-sqlite-persistent-queue.md)).
- Pendiente para el prototipo: medir ffmpeg y deno en un equipo modesto.
