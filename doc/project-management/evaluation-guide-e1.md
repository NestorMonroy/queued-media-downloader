# Guion de evaluación de E1 en Windows (T19)

- **Rol:** Evaluador en Windows ([caso de desarrollo](../process/development-case.md)).
- **Criterios:** sección 5 del [plan de la iteración E1](iteration-plan-e1.md#5-criterios-de-evaluación).
- **Duración estimada:** una hora, la mayor parte en `uv sync` y en las pruebas.

El Evaluador sigue los pasos en orden, anota cada resultado en la [tabla de resultados](#registro-de-resultados) y entrega los archivos indicados. No corrige el código: si un paso falla, registra la salida y continúa con los pasos que no dependan de él.

## Requisitos previos

**Del Responsable del proyecto, antes de empezar:**

1. Crear el repositorio en GitHub (la visibilidad sigue pendiente, [ADR-0020](../notes/adr-0020-repository-branching-and-lfs.md)).
2. Subir `main` con sus objetos de Git LFS (`git push -u origin main` desde un clon con Git LFS instalado). La subida añade unos 149 MiB a la cuota de LFS.
3. Comunicar al Evaluador la URL del repositorio.

**Del equipo del Evaluador:**

| Requisito | Comprobación |
|---|---|
| Windows 10 22H2 o Windows 11, x64 | `winver` |
| Smart App Control desactivado o en evaluación ([ADR-0026](../notes/adr-0026-smart-app-control-precondition.md)) | El comando de abajo devuelve `0` o `2`, o no existe el valor |
| Git con Git LFS | `git lfs version` |
| uv | `uv --version` (si falta: `winget install astral-sh.uv`) |
| PowerShell 5.1 o posterior | `$PSVersionTable.PSVersion` |
| Conexión a internet y unos 2 GB libres | — |

No hace falta Python instalado ni permisos de administrador (UC-01).

Comprobación de Smart App Control:

```powershell
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy' -ErrorAction SilentlyContinue).VerifiedAndReputablePolicyState
```

Si devuelve `1`, Smart App Control está bloqueando y Windows impedirá ejecutar uv y la build de ffmpeg, que no están firmados. Desactivarlo es una decisión de seguridad que corresponde a quien administra el equipo (Seguridad de Windows → Control de aplicaciones y del explorador → Smart App Control). La alternativa es evaluar en otro equipo o en una máquina virtual sin Smart App Control; en ese caso, anotarlo, porque la medición de memoria representa peor un equipo real.

## Pasos

Todos los comandos se ejecutan en PowerShell, en la carpeta del clon salvo que se indique otra cosa.

### Paso 1. Clonar el repositorio (UC-01, flujo básico, paso 1)

```powershell
git clone <URL del repositorio> queued-media-downloader
cd queued-media-downloader
git lfs ls-files
```

**Esperado:** `git lfs ls-files` lista los 9 archivos de `vendor/ffmpeg/n9.0.2-39-g7adfbe40dc-win64-lgpl-shared/bin/` con un `*` (descargados). Un `-` significa que solo hay punteros: anotar y ejecutar `git lfs pull`.

### Paso 2. Preparar el entorno (UC-01, pasos 2 y 3)

```powershell
uv sync
```

**Esperado:** termina sin errores y crea `.venv`. Anotar el tiempo aproximado.

### Paso 3. Comprobaciones locales (criterio 1)

```powershell
uv run ruff format --check
uv run ruff check
uv run mypy
uv run lint-imports
uv run pytest
```

**Esperado:** las cinco terminan con código `0` (`echo $LASTEXITCODE` tras cada una). En Windows, `pytest` omite 2 pruebas que usan scripts POSIX, y las pruebas de extremo a extremo usan el ffmpeg incluido.

### Paso 4. Pruebas de Windows (criterio 2)

```powershell
uv run pytest -m windows -v
```

**Esperado:** 3 pruebas pasan. `ffmpeg.exe` y `ffprobe.exe` arrancan con sus DLL y responden a `-version`, y el localizador elige la build incluida.

### Paso 5. Diagnóstico del entorno (UC-01, pasos 4 a 9)

```powershell
uv run queued-media-downloader diagnose
echo $LASTEXITCODE
```

**Esperado:** código `0`. La línea de ffmpeg es `[ OK ]` y dice `bundled`, y la de deno es `[ OK ]` y apunta a `.venv\Scripts\deno.exe`. La base de datos queda en `schema version 2`. Guardar la salida.

### Paso 6. Medición de memoria: preparar (criterio 6)

En **otra ventana de PowerShell**, en la carpeta del clon, pegar y ejecutar este script. Mide el pico de memoria (working set) de cada proceso del programa y lo muestra al pulsar `Ctrl+C`:

```powershell
$venv = (Resolve-Path .venv).Path
$peaks = @{}
Write-Host "Midiendo cada 0,5 s. Pulsar Ctrl+C cuando termine run."
try {
    while ($true) {
        Get-CimInstance Win32_Process |
            Where-Object { $_.Name -in 'python.exe', 'ffmpeg.exe', 'deno.exe' } |
            ForEach-Object {
                $role = switch ($_.Name) {
                    'ffmpeg.exe' { 'ffmpeg' }
                    'deno.exe' { 'deno' }
                    default {
                        if ($_.CommandLine -match '--multiprocessing-fork') { 'worker' }
                        elseif ($_.CommandLine -match 'queued-media-downloader') { 'principal' }
                        else { $null }
                    }
                }
                # El python.exe del entorno virtual es un lanzador: arranca el
                # Python real que instaló uv. Solo el real carga yt-dlp.
                if ($role -in 'worker', 'principal') {
                    $role += if ($_.ExecutablePath -like "$venv*") { ' lanzador' } else { ' real' }
                }
                $process = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
                if ($role -and $process) {
                    $key = "$role (PID $($_.ProcessId))"
                    if (-not $peaks.ContainsKey($key) -or $peaks[$key] -lt $process.PeakWorkingSet64) {
                        $peaks[$key] = $process.PeakWorkingSet64
                    }
                }
            }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    $peaks.GetEnumerator() | Sort-Object Name | ForEach-Object {
        '{0,-32} {1,8:N1} MiB' -f $_.Name, ($_.Value / 1MB)
    }
}
```

Para SUP-P04 cuentan los procesos `real`; los `lanzador` solo reenvían al Python real. Si el script falla, anotar el error y medir con el Administrador de tareas: en la pestaña Detalles, añadir la columna «Espacio de trabajo máximo (memoria)».

### Paso 7. Descarga real de YouTube con unión de audio y video (criterios 3 y 4)

En la primera ventana, con el script del paso 6 en marcha:

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw" --audio-only
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=jNQXAC9IVRw"
uv run queued-media-downloader run
echo $LASTEXITCODE
```

El video elegido es corto (19 s), estable y el que yt-dlp usa en sus propias pruebas.

Antes de repetir este paso, borrar `state\` y la carpeta de descargas para empezar sin jobs ni archivos previos.

**Esperado:**
- Código `0` y la línea `Using bundled ffmpeg: ffmpeg version n9.0.2-39-g7adfbe40dc-20261031`.
- **Job 1:** `format` con dos formatos unidos (en la primera evaluación, `395+251`: video AV1 y audio Opus), `running Merger` y `completed, saved to …\Downloads\queued-media-downloader\Me at the zoo [jNQXAC9IVRw].webm`. La extensión depende de los formatos que sirva YouTube.
- **Job 2:** solo audio, en la subcarpeta `audio` (`…\audio\Me at the zoo [jNQXAC9IVRw].opus`, T23). La extensión es la del audio original, sin recodificar.
- **Job 3:** `skipped: already downloaded or in the queue` (UC-03 A1).
- Ninguna línea `ERROR:` ni `WARNING:` en la consola (T20).

Al terminar `run`, pulsar `Ctrl+C` en la segunda ventana y guardar la tabla que muestra.

Comprobar los archivos descargados con el ffprobe incluido:

```powershell
$ffprobe = ".\vendor\ffmpeg\n9.0.2-39-g7adfbe40dc-win64-lgpl-shared\bin\ffprobe.exe"
$downloads = "$HOME\Downloads\queued-media-downloader"
Get-ChildItem $downloads -Recurse -File | ForEach-Object {
    "$($_.FullName.Substring($downloads.Length + 1)): $(& $ffprobe -v error -show_entries stream=codec_type -of csv=p=0 $_.FullName)"
}
```

**Esperado:** dos archivos. El de la carpeta principal tiene `video` y `audio`; el de `audio\`, solo `audio`. Si el video falta, se repitió el defecto de T23.

### Paso 8. Procesos al terminar (criterio 5, SUP-R02)

```powershell
Get-Process ffmpeg, deno -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '--multiprocessing-fork' }
```

**Esperado:** ninguna de las dos órdenes muestra procesos.

### Paso 9. Fallo controlado (UC-01 A6 y UC-03 A2)

```powershell
uv run queued-media-downloader enqueue "https://www.youtube.com/watch?v=00000000000"
uv run queued-media-downloader run
echo $LASTEXITCODE
```

**Esperado:** el job queda `failed (UNAVAILABLE)` con un mensaje en una sola línea, `run` termina con código `1` y muestra la ruta del log, `state\logs\queued-media-downloader.log`, que contiene el error completo.

## Registro de resultados

| Paso | Criterio | Resultado (sí/no) | Observaciones |
|---|---|---|---|
| 0. Smart App Control desactivado o en evaluación | — | | Equipo físico o máquina virtual: |
| 1. Clon con Git LFS | 3 | | |
| 2. `uv sync` | 3 | | Tiempo: |
| 3. Cinco comprobaciones | 1 | | Pruebas pasadas, omitidas y fallidas: |
| 4. `pytest -m windows` | 2 | | |
| 5. `diagnose` | 3 | | |
| 7. YouTube: unión, solo audio y duplicado | 3, 4 | | Formato elegido: |
| 8. Sin procesos al terminar | 5 | | |
| 9. Fallo controlado | — | | |

**Memoria máxima (paso 6, criterio 6):**

| Proceso | Pico (MiB) |
|---|---|
| Principal (`python.exe`, proceso `real`) | |
| Worker (`python.exe --multiprocessing-fork`, proceso `real`) | |
| ffmpeg | |
| deno | |

**Entregar al Responsable:**
- esta tabla rellenada;
- la salida completa de los pasos 3, 4, 5, 7 y 9;
- el archivo `state\logs\queued-media-downloader.log`;
- la versión exacta de Windows (`winver`).

## Después de la evaluación

- El **Responsable** fija SUP-P04 a partir del pico del proceso principal más el del worker, actualiza la lista de riesgos y completa la sección 6 del plan.
- Cada fallo se convierte en una tarea con su prueba antes de cerrar la iteración.
