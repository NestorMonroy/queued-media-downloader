# UC-01: Instalar y verificar el entorno

- **Objetivo:** el entorno queda instalado y verificado, listo para descargar, siguiendo solo el README.
- **Actor principal:** User
- **Disparador:** el User quiere usar el programa por primera vez, o tras actualizar el clon.
- **Significativo para la arquitectura:** sí
- **Decisiones relacionadas:** [ADR-0003](../../notes/adr-0003-packaging-with-uv-and-pyproject.md), [ADR-0005](../../notes/adr-0005-vendored-ffmpeg-lgpl-shared.md), [ADR-0006](../../notes/adr-0006-ffmpeg-resolution-and-verification.md), [ADR-0018](../../notes/adr-0018-ffmpeg-build-selection.md), [ADR-0020](../../notes/adr-0020-repository-branching-and-lfs.md)

## Breve descripción

El User obtiene el proyecto, prepara el entorno con uv y comprueba que ffmpeg, ffprobe, deno y la base de datos están listos para usarse.

## Precondiciones

- Windows 10/11 x64.
- Smart App Control desactivado o en modo de evaluación ([ADR-0026](../../notes/adr-0026-smart-app-control-precondition.md)).
- uv instalado (por ejemplo, `winget install astral-sh.uv`).
- Git con Git LFS instalado, si el proyecto se obtiene con `git clone`.
- Conexión a internet.

## Flujo básico

1. El User clona el repositorio (`git clone`); Git LFS descarga los binarios de `vendor/ffmpeg/`.
2. El User ejecuta `uv sync`.
3. uv descarga un Python ≥3.11 si no hay uno compatible, crea `.venv` e instala las versiones exactas de `uv.lock` (yt-dlp, deno y el resto de dependencias).
4. El User ejecuta `uv run queued-media-downloader diagnose`.
5. El sistema carga y valida la configuración.
6. El sistema localiza ffmpeg siguiendo el orden de ADR-0006 (ruta configurada, `vendor/ffmpeg/`, `PATH`).
7. El sistema verifica que `ffmpeg.exe` y `ffprobe.exe` existen y responden a `-version`, y calcula su SHA-256 si no lo tiene en caché o si el archivo cambió.
8. El sistema verifica que deno está disponible y que la base de datos se abre y tiene las migraciones aplicadas (las aplica si faltan).
9. El sistema muestra, en inglés, la versión y la ruta de cada componente y el resultado de cada comprobación, y termina con código de salida `0`.

## Flujos alternativos

- **A1. Clonado sin Git LFS** (paso 7): los binarios son punteros de texto de ~130 bytes. El sistema lo detecta, indica ejecutar `git lfs pull` y termina con código `2`.
- **A2. Cuota de Git LFS agotada** (paso 1): Git LFS no descarga los binarios y el repositorio queda con punteros. Continúa como A1; el mensaje menciona además la posibilidad de configurar `ffmpeg_path` con un ffmpeg propio.
- **A3. Plataforma no soportada** (paso 3): uv se detiene con un error de plataforma por la restricción `[tool.uv] environments` (por ejemplo, en Windows ARM64).
- **A4. ffmpeg desde `PATH`** (paso 6): no hay ruta configurada ni binarios en `vendor/ffmpeg/`, pero sí un ffmpeg en el `PATH`. El sistema lo usa y avisa de que su versión no está validada.
- **A5. Binario corrupto** (paso 7): el SHA-256 no coincide con el registrado en `SOURCE.md` o el binario no responde a `-version`. El sistema lo indica y termina con código `2`.
- **A6. Configuración no válida** (paso 5): el sistema indica la clave y el valor no válidos y termina con código `2`.
- **A7. Smart App Control activado** (paso 2 o posteriores): Windows bloquea `uv.exe`, o un binario sin firmar del proyecto, con el mensaje "Una directiva de Control de aplicaciones bloqueó este archivo". El sistema no llega a ejecutarse, así que no puede informar; el User comprueba la precondición ([ADR-0026](../../notes/adr-0026-smart-app-control-precondition.md)).
- **A8. La base de datos no se puede abrir o una migración falla** (paso 8): la migración se deshace (la base de datos queda en su última versión completa) y se cierra la conexión. `diagnose` muestra la comprobación `database` como fallida, con la causa, y termina con código `2`; los demás comandos indican la ruta y la causa sin traza y terminan con código `1` (si otro proceso la tiene ocupada más allá de `busy_timeout`, `the queue is busy`).
- **A9. Sin conexión** (propuesto, [UC-11](uc-11-preserve-jobs-under-external-conditions.md) A2): `diagnose` resuelve el nombre de los sitios configurados (por defecto, `www.youtube.com`) sin descargar nada; si falla, muestra la comprobación `network` como aviso, no como fallo, porque el entorno está instalado.
- **A10. Destino o estado no utilizables** (propuesto): `diagnose` comprueba que `download_directory` y `state_directory` existen, admiten escritura y tienen espacio libre por encima de `min_free_disk_mib` ([BR-08](../business-rules.md)). Si una carpeta aún no existe, el espacio se mide en la unidad de su antecesor existente más cercano. Si no, muestra la carpeta y la causa. Una carpeta sin permiso es un fallo; poco espacio, un aviso. Origen: la comprobación previa del destino de VoiceStudio y la medición del espacio de VoiceBlueprintPro.
- **A11. Proxy en uso** (propuesto, decisión D-7): `diagnose` informa de si las descargas usarán un proxy, configurado o tomado del sistema (yt-dlp usa el del sistema si no se configura otro), sin mostrar credenciales (SUP-SEC01).

## Postcondiciones

- **Éxito:** entorno listo y reproducible; el estado de verificación de ffmpeg queda guardado en `state/` para no recalcular el hash en cada arranque.
- **Fallo:** el User recibe una acción concreta para corregir el problema.

## Requisitos especiales

- Ningún paso requiere Python preinstalado ni permisos de administrador.
- La verificación completa (con hash) se ejecuta solo cuando hace falta; la comprobación de arranque de `run` reutiliza el estado guardado.

## Reglas, requisitos y restricciones asociados

- **Reglas:** ninguna regla de la cola; A10 usa BR-08 y A11, BR-12.
- **Requisitos suplementarios:** SUP-U01, SUP-U03, SUP-O02, SUP-C01, SUP-C03, SUP-L02; SUP-SEC01 (A11).
- **Restricciones:** sin permisos de administrador ni Python preinstalado; Smart App Control desactivado (ADR-0026).
- **Dependencias:** ninguna; es la precondición de los demás casos de uso.

## Criterios de aceptación

1. Siguiendo solo el README, un equipo limpio con Windows 10/11 x64 queda listo con `diagnose` en código `0`.
2. Cada comprobación fallida indica una acción concreta y termina con el código de su flujo (A1, A5, A6: `2`; A8: `2` en `diagnose`).
3. La segunda ejecución de `diagnose` reutiliza el estado guardado de ffmpeg y no recalcula el hash.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Orden de localización (configurada, `vendor/`, `PATH`) | Cualquier sistema |
| Detección de puntero de Git LFS (A1, A2) | Cualquier sistema |
| Caché del hash por tamaño y fecha | Cualquier sistema |
| Configuración no válida (A6) | Cualquier sistema |
| Migraciones: base nueva, actualización desde cada versión (1, 2), conservación de datos, integridad referencial e índices, migración fallida deshecha (A8) | Cualquier sistema |
| `ffmpeg.exe` y `ffprobe.exe` incluidos arrancan con sus DLL | **Windows** |
| Flujo completo desde un clon nuevo | **Windows**, manual, al cerrar la iteración |
