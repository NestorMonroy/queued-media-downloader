# Funciones de ayuda de la campaña final de validación en Windows (T42).
#
# Uso, en PowerShell, desde la raíz del clon:
#     . .\scripts\windows\t42_campaign.ps1
#
# Guion completo: doc/project-management/windows-validation-campaign.md.
# Nunca usa ni borra la cola, la configuración ni las descargas reales: cada
# bloque trabaja en C:\qmd-t42\<bloque> y la evidencia queda en
# C:\qmd-t42\evidence. No se ha ejecutado en el entorno de desarrollo (Linux):
# su primera ejecución forma parte de la campaña.

Set-StrictMode -Version Latest

$script:CampaignRoot = "C:\qmd-t42"
$script:EvidenceDirectory = Join-Path $script:CampaignRoot "evidence"

function Initialize-CampaignEvidence {
    New-Item -ItemType Directory -Force -Path $script:EvidenceDirectory | Out-Null
}

function Test-CampaignCommit {
    # Se detiene si el clon no está limpio o no está en el commit evaluado.
    param([Parameter(Mandatory)][string]$ExpectedCommit)
    $head = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "git rev-parse failed (exit code $LASTEXITCODE)" }
    if ($head -ne $ExpectedCommit) {
        throw "The clone is at $head, not at the evaluated commit $ExpectedCommit"
    }
    $changes = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "git status failed (exit code $LASTEXITCODE)" }
    if ($changes) { throw "The clone has local changes:`n$changes" }
    if (Test-Path ".\config.toml") { throw "Remove config.toml from the clone first" }
    Write-Host "Evaluated commit confirmed: $head"
}

function Save-CampaignEnvironment {
    # Versiones de las herramientas y commit evaluado, para el registro.
    Initialize-CampaignEvidence
    $lines = @(
        "date: $(Get-Date -Format o)",
        "commit: $((git rev-parse HEAD).Trim())",
        "windows: $((Get-CimInstance Win32_OperatingSystem).Caption) $((Get-CimInstance Win32_OperatingSystem).Version)",
        "architecture: $env:PROCESSOR_ARCHITECTURE",
        "uv: $(uv --version)",
        "python: $(uv run python --version)",
        "git: $(git --version)",
        "git-lfs: $(git lfs version)"
    )
    $path = Join-Path $script:EvidenceDirectory "environment.txt"
    $lines | Set-Content -Encoding utf8 $path
    Write-Host "Saved $path"
}

function New-CampaignQueue {
    # Cola aislada para un bloque: nunca reutiliza ni borra una carpeta.
    param([Parameter(Mandatory)][string]$Block)
    $root = Join-Path $script:CampaignRoot $Block
    if (Test-Path $root) {
        throw "$root already exists; choose another block name (nothing was deleted)"
    }
    $state = Join-Path $root "state"
    $downloads = Join-Path $root "downloads"
    New-Item -ItemType Directory -Path $state, $downloads | Out-Null
    $env:QUEUED_MEDIA_DOWNLOADER_STATE_DIRECTORY = $state
    $env:QUEUED_MEDIA_DOWNLOADER_DOWNLOAD_DIRECTORY = $downloads
    Write-Host "Queue for block ${Block}: state $state, downloads $downloads"
}

function Invoke-CampaignStep {
    # Ejecuta una orden, guarda su salida completa y devuelve su código de salida.
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Command
    )
    Initialize-CampaignEvidence
    $log = Join-Path $script:EvidenceDirectory "$Name.log"
    $executable = $Command[0]
    $arguments = @($Command | Select-Object -Skip 1)
    # Start-Process con -Wait conserva el código de salida real del proceso.
    $process = Start-Process -FilePath $executable -ArgumentList $arguments `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError "$log.stderr"
    $code = $process.ExitCode
    Add-Content -Encoding utf8 (Join-Path $script:EvidenceDirectory "exit-codes.txt") "${Name}: $code"
    Write-Host "${Name}: exit code $code (output in $log)"
    return $code
}

function Invoke-CampaignSuites {
    # Paso 3. Las suites de pytest se ejecutan sin las variables de la cola de
    # la campaña: las pruebas crean sus propias carpetas temporales.
    Remove-Item Env:QUEUED_MEDIA_DOWNLOADER_* -ErrorAction SilentlyContinue
    $results = [ordered]@{}
    $results["run_checks"] = Invoke-CampaignStep "step3-run-checks" @("uv", "run", "python", "scripts/run_checks.py")
    $results["pytest_windows"] = Invoke-CampaignStep "step3-pytest-windows" @("uv", "run", "pytest", "-m", "windows", "-o", "addopts=")
    $results["pytest_network"] = Invoke-CampaignStep "step3-pytest-network" @("uv", "run", "pytest", "-m", "network", "-o", "addopts=")
    $results.GetEnumerator() | ForEach-Object { "{0,-16} exit code {1}" -f $_.Key, $_.Value }
    if (($results.Values | Where-Object { $_ -ne 0 }).Count -gt 0) {
        Write-Warning "At least one suite failed: record it and classify the defects"
    }
}

function Save-CampaignProcesses {
    # Pasos 6 a 8: procesos del programa que siguen vivos.
    param([Parameter(Mandatory)][string]$Name)
    Initialize-CampaignEvidence
    $path = Join-Path $script:EvidenceDirectory "processes-$Name.txt"
    Get-Process ffmpeg, ffprobe, deno, python -ErrorAction SilentlyContinue |
        Select-Object Name, Id, StartTime, Path |
        Format-Table -AutoSize | Out-String -Width 200 |
        Set-Content -Encoding utf8 $path
    Write-Host "Saved $path"
}
