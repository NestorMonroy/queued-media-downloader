# Funciones de ayuda de la campaña final de validación en Windows (T42).
#
# Uso, en PowerShell (Windows PowerShell 5.1 o PowerShell 7), desde la raíz
# del clon:
#     . .\scripts\windows\t42_campaign.ps1
#     Test-CampaignCandidate "t42-candidate-1"
#
# Guion completo: doc/project-management/windows-validation-campaign.md.
#
# Nunca usa la cola, la configuración ni las descargas reales: todo queda en
# C:\qmd-t42\<etiqueta>\, una carpeta por candidato. Ninguna función borra
# archivos.
#
# No se ha ejecutado en el entorno de desarrollo (Linux, sin PowerShell): su
# primera ejecución forma parte de la campaña, y un fallo suyo se clasifica
# como defecto de herramienta de la campaña.

Set-StrictMode -Version Latest

$script:CampaignBase = "C:\qmd-t42"
$script:CandidateRoot = $null

function Assert-CampaignCandidate {
    if (-not $script:CandidateRoot) {
        throw "Run Test-CampaignCandidate first: it confirms the evaluated commit"
    }
}

function Get-CampaignEvidenceDirectory {
    Assert-CampaignCandidate
    $directory = Join-Path $script:CandidateRoot "evidence"
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    return $directory
}

function Get-NewEvidencePath {
    # Ruta de evidencia que nunca sobrescribe otra: name.log, name-2.log...
    param([Parameter(Mandatory)][string]$Name, [string]$Extension = "log")
    $directory = Get-CampaignEvidenceDirectory
    $path = Join-Path $directory "$Name.$Extension"
    $attempt = 2
    while (Test-Path $path) {
        $path = Join-Path $directory "$Name-$attempt.$Extension"
        $attempt += 1
    }
    return $path
}

function Test-CampaignCandidate {
    # Confirma que el clon está limpio y en la etiqueta indicada, y que la
    # etiqueta de GitHub apunta al mismo commit. Registra el hash real.
    param([Parameter(Mandatory)][string]$Tag)
    $tagCommit = git rev-parse --verify "refs/tags/$Tag^{commit}"
    if ($LASTEXITCODE -ne 0) { throw "Tag $Tag does not exist in the clone (git fetch --tags)" }
    $tagCommit = "$tagCommit".Trim()
    $head = "$(git rev-parse HEAD)".Trim()
    if ($LASTEXITCODE -ne 0) { throw "git rev-parse HEAD failed (exit code $LASTEXITCODE)" }
    if ($head -ne $tagCommit) {
        throw "The clone is at $head, but $Tag is $tagCommit (git checkout $Tag)"
    }
    $changes = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "git status failed (exit code $LASTEXITCODE)" }
    if ($changes.Count -gt 0) { throw "The clone has local changes:`n$($changes -join "`n")" }
    if (Test-Path ".\config.toml") { throw "Remove config.toml from the clone first" }
    $remoteLines = @(git ls-remote origin "refs/tags/$Tag" "refs/tags/$Tag^{}")
    if ($LASTEXITCODE -ne 0) { throw "git ls-remote failed (exit code $LASTEXITCODE)" }
    # Una etiqueta anotada aparece dos veces; la línea terminada en ^{} da el commit.
    $peeled = @($remoteLines | Where-Object { $_ -match "\^\{\}$" })
    if ($peeled.Count -gt 0) { $remoteLine = $peeled[0] }
    elseif ($remoteLines.Count -gt 0) { $remoteLine = $remoteLines[0] }
    else { $remoteLine = "" }
    $remoteCommit = ($remoteLine -split "\s+")[0]
    if ($remoteCommit -ne $tagCommit) {
        throw "On GitHub, $Tag is '$remoteCommit', not $tagCommit"
    }
    $script:CandidateRoot = Join-Path $script:CampaignBase $Tag
    New-Item -ItemType Directory -Force -Path $script:CandidateRoot | Out-Null
    $path = Get-NewEvidencePath "candidate" "txt"
    @(
        "tag: $Tag",
        "commit: $tagCommit",
        "github commit: $remoteCommit",
        "checked at: $(Get-Date -Format o)"
    ) | Set-Content -Encoding utf8 $path
    Write-Host "Evaluated candidate confirmed: $Tag = $tagCommit (saved in $path)"
}

function Save-CampaignEnvironment {
    # Versiones de las herramientas, para el registro.
    $path = Get-NewEvidencePath "environment" "txt"
    $os = Get-CimInstance Win32_OperatingSystem
    @(
        "date: $(Get-Date -Format o)",
        "commit: $("$(git rev-parse HEAD)".Trim())",
        "windows: $($os.Caption) $($os.Version) build $($os.BuildNumber)",
        "architecture: $env:PROCESSOR_ARCHITECTURE",
        "powershell: $($PSVersionTable.PSVersion)",
        "uv: $(uv --version)",
        "python: $(uv run python --version)",
        "git: $(git --version)",
        "git-lfs: $(git lfs version)"
    ) | Set-Content -Encoding utf8 $path
    Write-Host "Saved $path"
}

function New-CampaignQueue {
    # Cola aislada para un bloque: nunca reutiliza ni borra una carpeta.
    param([Parameter(Mandatory)][string]$Block)
    Assert-CampaignCandidate
    $root = Join-Path (Join-Path $script:CandidateRoot "queues") $Block
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

function Invoke-CampaignStep {
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
    # En Windows PowerShell 5.1, la salida de error de un programa llega como
    # registros de error: con Stop, la orden se cortaría a medias.
    $ErrorActionPreference = "Continue"
    try {
        & $executable @arguments 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log | Out-Host
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    $codes = Join-Path (Get-CampaignEvidenceDirectory) "exit-codes.txt"
    Add-Content -Encoding utf8 $codes "$(Get-Date -Format o) ${Name}: $code ($log)"
    Write-Host "${Name}: exit code $code (output in $log)"
    return $code
}

function Invoke-CampaignSuites {
    # Paso 3. Las pruebas crean sus propias carpetas temporales: se ejecutan
    # sin las variables de la cola de la campaña.
    Assert-CampaignCandidate
    Remove-Item Env:QUEUED_MEDIA_DOWNLOADER_* -ErrorAction SilentlyContinue
    $results = [ordered]@{}
    $results["run_checks"] = Invoke-CampaignStep "step3-run-checks" @("uv", "run", "python", "scripts/run_checks.py")
    $results["pytest_windows"] = Invoke-CampaignStep "step3-pytest-windows" @("uv", "run", "pytest", "-m", "windows", "-o", "addopts=")
    $results["pytest_network"] = Invoke-CampaignStep "step3-pytest-network" @("uv", "run", "pytest", "-m", "network", "-o", "addopts=")
    foreach ($entry in $results.GetEnumerator()) {
        Write-Host ("{0,-16} exit code {1}" -f $entry.Key, $entry.Value)
    }
    $failed = @($results.Values | Where-Object { $_ -ne 0 })
    if ($failed.Count -gt 0) {
        Write-Warning "At least one suite failed: record it and classify the defects"
    }
    Write-Host "Call New-CampaignQueue before the next step: the queue variables were cleared"
}

function Save-CampaignQueueState {
    # Salida de list en la cola aislada actual (pasos 5 a 12).
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Test-Path Env:QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY)) {
        throw "No campaign queue is active: call New-CampaignQueue first"
    }
    Invoke-CampaignStep "queue-$Name" @("uv", "run", "queued-media-downloader", "list") | Out-Null
}

function Save-CampaignProcesses {
    # Pasos 6 a 8: procesos del programa que siguen vivos.
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
