# Funciones de ayuda de la validación en Windows (guion:
# doc/project-management/windows-validation-campaign.md).
#
# Uso, en PowerShell 7 o Windows PowerShell 5.1, desde la raíz del clon:
#     . .\scripts\windows\validation_campaign.ps1
#     Start-ValidationRun
#
# Cada ejecución se identifica por el commit evaluado y su instante de
# arranque, sin etiquetas de Git: <raíz>\runs\<aaaammdd-hhmmss>-<commit>\.
# La raíz es, por orden: el parámetro -EvidenceRoot, la variable de entorno
# QMD_VALIDATION_ROOT o C:\qmd-validation.
#
# Nunca usa la cola, la configuración ni las descargas reales del usuario, y
# ninguna función borra archivos: cada ejecución y cada cola usan carpetas
# nuevas, y la evidencia nunca se sobrescribe.

Set-StrictMode -Version Latest

$script:DefaultEvidenceRoot = "C:\qmd-validation"
$script:RunDirectory = $null
$script:RunCommit = $null

function Get-ValidationEvidenceRoot {
    param([string]$EvidenceRoot)
    if ($EvidenceRoot) { return $EvidenceRoot }
    if (Test-Path Env:QMD_VALIDATION_ROOT) {
        return $env:QMD_VALIDATION_ROOT
    }
    return $script:DefaultEvidenceRoot
}

function Get-GitOutput {
    # Salida de una orden de git, recortada; se detiene si git falla.
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed (exit code $LASTEXITCODE)" }
    return "$output".Trim()
}

function Assert-ValidationRun {
    # La evidencia de una ejecución solo puede venir de su commit.
    if (-not $script:RunDirectory) {
        throw "Run Start-ValidationRun (or Resume-ValidationRun) first"
    }
    $head = Get-GitOutput @("rev-parse", "HEAD")
    if ($head -ne $script:RunCommit) {
        throw "The clone moved from $($script:RunCommit) to ${head}: start a new run with Start-ValidationRun"
    }
}

function Get-ValidationEvidenceDirectory {
    Assert-ValidationRun
    $directory = Join-Path $script:RunDirectory "evidence"
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    return $directory
}

function Get-NewEvidencePath {
    # Ruta de evidencia que nunca sobrescribe otra: name.log, name-2.log...
    param([Parameter(Mandatory)][string]$Name, [string]$Extension = "log")
    $directory = Get-ValidationEvidenceDirectory
    $path = Join-Path $directory "$Name.$Extension"
    $attempt = 2
    while (Test-Path $path) {
        $path = Join-Path $directory "$Name-$attempt.$Extension"
        $attempt += 1
    }
    return $path
}

function Start-ValidationRun {
    # Comprueba que el clon está limpio y en el estado publicado de main,
    # crea la carpeta de la ejecución y guarda el entorno y las versiones.
    param(
        [string]$EvidenceRoot,
        # Evalúa un commit que no es origin/main (por ejemplo, una rama de
        # corrección); queda registrado como no publicado en run.txt.
        [switch]$AllowUnpublishedCommit
    )
    Get-GitOutput @("fetch", "--quiet", "origin") | Out-Null
    $head = Get-GitOutput @("rev-parse", "HEAD")
    $publishedMain = Get-GitOutput @("rev-parse", "origin/main")
    $changes = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "git status failed (exit code $LASTEXITCODE)" }
    if ($changes.Count -gt 0) {
        throw "The clone has local changes that would invalidate the evidence:`n$($changes -join "`n")"
    }
    if (Test-Path ".\config.toml") { throw "Move config.toml out of the clone first" }
    $isPublished = $head -eq $publishedMain
    if (-not $isPublished -and -not $AllowUnpublishedCommit) {
        throw "The clone is at $head, but the published main is $publishedMain. Run: git switch main; git pull --ff-only origin main; uv sync"
    }
    $root = Get-ValidationEvidenceRoot $EvidenceRoot
    $runName = "$(Get-Date -Format 'yyyyMMdd-HHmmss')-$($head.Substring(0, 12))"
    $script:RunDirectory = Join-Path (Join-Path $root "runs") $runName
    $script:RunCommit = $head
    New-Item -ItemType Directory -Path $script:RunDirectory | Out-Null
    $branch = Get-GitOutput @("rev-parse", "--abbrev-ref", "HEAD")
    @(
        "commit: $head",
        "published main: $publishedMain",
        "commit is the published main: $isPublished",
        "branch: $branch",
        "started at: $(Get-Date -Format o)",
        "run directory: $($script:RunDirectory)"
    ) | Set-Content -Encoding utf8 (Join-Path $script:RunDirectory "run.txt")
    Write-Host "Validation run $runName for commit $head"
    Write-Host "  evidence in $($script:RunDirectory)"
    Save-ValidationEnvironment
}

function Resume-ValidationRun {
    # Retoma una ejecución en otra ventana de PowerShell (por ejemplo, para
    # medir la memoria); sin -RunDirectory, la más reciente de la raíz.
    param([string]$RunDirectory, [string]$EvidenceRoot)
    if (-not $RunDirectory) {
        $runs = Join-Path (Get-ValidationEvidenceRoot $EvidenceRoot) "runs"
        $latest = Get-ChildItem -Directory $runs -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -Last 1
        if (-not $latest) { throw "There is no validation run in $runs" }
        $RunDirectory = $latest.FullName
    }
    $commitLine = Get-Content (Join-Path $RunDirectory "run.txt") |
        Where-Object { $_ -like "commit: *" } | Select-Object -First 1
    $script:RunDirectory = $RunDirectory
    $script:RunCommit = $commitLine.Substring("commit: ".Length)
    Assert-ValidationRun
    Write-Host "Resumed validation run $RunDirectory"
}

function Save-ValidationEnvironment {
    # Plataforma y herramientas; versiones exactas de las dependencias;
    # versiones de ffmpeg, yt-dlp, yt-dlp-ejs y deno según diagnose.
    $path = Get-NewEvidencePath "environment" "txt"
    $os = Get-CimInstance Win32_OperatingSystem
    @(
        "date: $(Get-Date -Format o)",
        "commit: $($script:RunCommit)",
        "windows: $($os.Caption) $($os.Version) build $($os.BuildNumber)",
        "architecture: $env:PROCESSOR_ARCHITECTURE",
        "powershell: $($PSVersionTable.PSVersion)",
        "uv: $(uv --version)",
        "python: $(uv run python --version)",
        "git: $(git --version)",
        "git-lfs: $(git lfs version)"
    ) | Set-Content -Encoding utf8 $path
    Write-Host "Saved $path"
    Invoke-ValidationStep "dependencies" @("uv", "pip", "freeze") | Out-Null
    New-ValidationQueue "diagnose"
    Invoke-ValidationStep "diagnose" @("uv", "run", "queued-media-downloader", "diagnose") | Out-Null
}

function New-ValidationQueue {
    # Cola aislada para un bloque de la ejecución: nunca reutiliza ni borra
    # una carpeta.
    param([Parameter(Mandatory)][string]$Block)
    Assert-ValidationRun
    $root = Join-Path (Join-Path $script:RunDirectory "queues") $Block
    if (Test-Path $root) {
        throw "$root already exists; use another block name, such as '$Block-r2' (nothing was deleted)"
    }
    $state = Join-Path $root "state"
    $downloads = Join-Path $root "downloads"
    New-Item -ItemType Directory -Path $state, $downloads | Out-Null
    $env:QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY = $state
    $env:QUEUED_MEDIA_DOWNLOADER_DOWNLOAD_DIRECTORY = $downloads
    Write-Host "Queue for block ${Block}:"
    Write-Host "  state     $state"
    Write-Host "  downloads $downloads"
}

function Invoke-ValidationStep {
    # Ejecuta un programa, muestra y guarda su salida y devuelve su código de
    # salida real: $LASTEXITCODE es el del propio programa, no el de la tubería.
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Command
    )
    $log = Get-NewEvidencePath $Name
    $executable = $Command[0]
    $arguments = @($Command | Select-Object -Skip 1)
    $previousPreference = $ErrorActionPreference
    $previousOutputEncoding = [Console]::OutputEncoding
    $previousPythonEncoding = $env:PYTHONIOENCODING
    # En Windows PowerShell 5.1, la salida de error de un programa llega como
    # registros de error: con Stop, la orden se cortaría a medias.
    $ErrorActionPreference = "Continue"
    # Con la salida redirigida, Python escribe en cp1252 y PowerShell la lee
    # con otra codificación: los títulos llegaban a la evidencia con "?" y
    # rayas como U+FFFD. En UTF-8 por los dos lados, la evidencia los conserva.
    $env:PYTHONIOENCODING = "utf-8"
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    try {
        & $executable @arguments 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log | Out-Host
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
        [Console]::OutputEncoding = $previousOutputEncoding
        $env:PYTHONIOENCODING = $previousPythonEncoding
    }
    $codes = Join-Path (Get-ValidationEvidenceDirectory) "exit-codes.txt"
    Add-Content -Encoding utf8 $codes "$(Get-Date -Format o) ${Name}: $code ($log)"
    Write-Host "${Name}: exit code $code (output in $log)"
    return $code
}

function Invoke-ValidationSuites {
    # Las cinco verificaciones y las pruebas windows y network. Las pruebas
    # crean sus propias carpetas: se ejecutan sin las variables de la cola.
    Assert-ValidationRun
    Remove-Item Env:QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY, Env:QUEUED_MEDIA_DOWNLOADER_DOWNLOAD_DIRECTORY -ErrorAction SilentlyContinue
    $results = [ordered]@{}
    $results["run_checks"] = Invoke-ValidationStep "suite-run-checks" @("uv", "run", "python", "scripts/run_checks.py")
    $results["pytest_windows"] = Invoke-ValidationStep "suite-pytest-windows" @("uv", "run", "pytest", "-m", "windows", "-o", "addopts=")
    $results["pytest_network"] = Invoke-ValidationStep "suite-pytest-network" @("uv", "run", "pytest", "-m", "network", "-o", "addopts=")
    foreach ($entry in $results.GetEnumerator()) {
        Write-Host ("{0,-16} exit code {1}" -f $entry.Key, $entry.Value)
    }
    $failed = @($results.Values | Where-Object { $_ -ne 0 })
    if ($failed.Count -gt 0) {
        Write-Warning "At least one suite failed: record it and classify the defects"
    }
    Write-Host "Call New-ValidationQueue before the next step: the queue variables were cleared"
}

function Invoke-ProcessTreeExperiment {
    # Experimento de terminación de árboles de procesos (ADR-0029); su JSON
    # queda en la evidencia de la ejecución.
    $json = Get-NewEvidencePath "process-tree-termination" "json"
    Invoke-ValidationStep "process-tree-termination" @(
        "uv", "run", "python", "scripts/experiments/process_tree_termination.py", "--json", $json
    )
}

function Save-ValidationQueueState {
    # Salida de list en la cola aislada actual.
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Test-Path Env:QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY)) {
        throw "No validation queue is active: call New-ValidationQueue first"
    }
    Invoke-ValidationStep "queue-$Name" @("uv", "run", "queued-media-downloader", "list") | Out-Null
}

function Save-ValidationProcesses {
    # Procesos del programa que siguen vivos (cancelación, cierres).
    param([Parameter(Mandatory)][string]$Name)
    $path = Get-NewEvidencePath "processes-$Name" "txt"
    $processes = @(Get-Process ffmpeg, ffprobe, deno, python -ErrorAction SilentlyContinue)
    if ($processes.Count -eq 0) {
        "No ffmpeg, ffprobe, deno or python process is running" | Set-Content -Encoding utf8 $path
    }
    else {
        $processes | Select-Object Name, Id, Path | Format-Table -AutoSize |
            Out-String -Width 300 | Set-Content -Encoding utf8 $path
    }
    Write-Host "Saved $path ($($processes.Count) processes)"
}

function Watch-ValidationMemory {
    # Pico de memoria (working set) de cada proceso del programa, cada 0,5 s,
    # hasta Ctrl+C (SUP-P04). Para SUP-P04 cuentan los procesos "real"; los
    # "launcher" son el python.exe del entorno virtual, que solo reenvía.
    param([Parameter(Mandatory)][string]$Name)
    $path = Get-NewEvidencePath "memory-$Name" "txt"
    $venv = (Resolve-Path .venv).Path
    $peaks = @{}
    Write-Host "Measuring every 0.5 s; press Ctrl+C when run finishes"
    try {
        while ($true) {
            $candidates = Get-CimInstance Win32_Process |
                Where-Object { $_.Name -in "python.exe", "ffmpeg.exe", "deno.exe" }
            foreach ($candidate in $candidates) {
                $role = $null
                if ($candidate.Name -eq "ffmpeg.exe") { $role = "ffmpeg" }
                elseif ($candidate.Name -eq "deno.exe") { $role = "deno" }
                elseif ("$($candidate.CommandLine)" -match "--multiprocessing-fork") { $role = "worker" }
                elseif ("$($candidate.CommandLine)" -match "queued-media-downloader") { $role = "main" }
                if ($role -in "worker", "main") {
                    if ("$($candidate.ExecutablePath)" -like "$venv*") { $role += " launcher" } else { $role += " real" }
                }
                $process = Get-Process -Id $candidate.ProcessId -ErrorAction SilentlyContinue
                if ($role -and $process) {
                    $key = "$role (PID $($candidate.ProcessId))"
                    if (-not $peaks.ContainsKey($key) -or $peaks[$key] -lt $process.PeakWorkingSet64) {
                        $peaks[$key] = $process.PeakWorkingSet64
                    }
                }
            }
            Start-Sleep -Milliseconds 500
        }
    }
    finally {
        $lines = @($peaks.GetEnumerator() | Sort-Object Name | ForEach-Object {
            "{0,-32} {1,8:N1} MiB" -f $_.Name, ($_.Value / 1MB)
        })
        if ($lines.Count -eq 0) { $lines = @("No process of the program was seen") }
        $lines | Set-Content -Encoding utf8 $path
        $lines | Out-Host
        Write-Host "Saved $path"
    }
}
