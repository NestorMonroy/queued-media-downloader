# ADR-0006: Resolución y verificación de ffmpeg

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** el comando `doctor` se llama `diagnose` desde [ADR-0014](adr-0014-use-case-structure-and-vocabulary.md).

## Contexto

Con ffmpeg en el repositorio ([ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md)) no hay paso de descarga, pero los binarios pueden faltar, estar corruptos o ser punteros de Git LFS si se clonó sin LFS. yt-dlp-gui busca los ejecutables en subcarpetas anidadas; ese enfoque es lento en discos modestos y ambiguo si hay varias copias.

## Decisión

**Orden de resolución explícito:**
1. Ruta configurada por el usuario (variable de entorno o configuración).
2. `vendor/ffmpeg/` del proyecto.
3. `PATH` del sistema, con aviso de versión no validada.

**Verificación automática al arrancar la cola,** antes de procesar trabajos:
- Existen `ffmpeg.exe` y `ffprobe.exe` y responden a `-version`.
- El SHA-256 completo se calcula solo la primera vez o cuando cambian el tamaño o la fecha del archivo (guardados en un archivo de estado).
- Si un binario es un puntero de Git LFS (archivo de texto de ~130 bytes), el mensaje indica ejecutar `git lfs pull`.

**Comando `doctor`:** muestra qué ffmpeg, ffprobe y deno se usan, sus versiones y el resultado de la verificación.

La ruta resultante se pasa a yt-dlp en el parámetro `ffmpeg_location`.

## Consecuencias

- Los fallos se detectan al inicio, no al final de una descarga.
- El usuario no ejecuta ningún paso de preparación.
- La lógica vive en un módulo de resolución independiente que la cola consulta antes de crear cada `YoutubeDL`, reutilizable por una GUI futura.
