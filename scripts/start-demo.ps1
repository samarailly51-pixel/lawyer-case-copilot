[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [ValidateRange(1024, 65535)]
    [int]$BackendPort = 8000,
    [ValidateRange(1024, 65535)]
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$runtimeDir = Join-Path $repoRoot ".demo-runtime"
$pidFile = Join-Path $runtimeDir "processes.json"
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath (Join-Path $backendDir "main.py"))) {
    throw "Could not verify the repository root: $repoRoot"
}

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Test-PortInUse([int]$Port) {
    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    return [bool]($listeners | Where-Object { $_.Port -eq $Port })
}

if (Test-Path -LiteralPath $pidFile) {
    $existing = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
    $backendRunning = Get-Process -Id $existing.backend_pid -ErrorAction SilentlyContinue
    $frontendRunning = Get-Process -Id $existing.frontend_pid -ErrorAction SilentlyContinue
    if ($backendRunning -and $frontendRunning) {
        $existingFrontendPort = if ($existing.frontend_port) { $existing.frontend_port } else { 5173 }
        Write-Host "Demo is already running: http://localhost:$existingFrontendPort" -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process "http://localhost:$existingFrontendPort" }
        exit 0
    }
}

if (Test-PortInUse $BackendPort) {
    Write-Error "Backend port $BackendPort is already in use. Stop the owning service or pass -BackendPort with an available port."
}
if (Test-PortInUse $FrontendPort) {
    Write-Error "Frontend port $FrontendPort is already in use. Stop the owning service or pass -FrontendPort with an available port."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "First run: creating a Python virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $launcherRows = @(& py -0p)
        $preferredRow = $launcherRows | Where-Object { $_ -match "3\.12" } | Select-Object -First 1
        if (-not $preferredRow) {
            $preferredRow = $launcherRows | Where-Object { $_ -match "3\.(1[1-9]|[2-9][0-9])" } | Select-Object -First 1
        }
        if ($preferredRow -and $preferredRow -match "([A-Za-z]:\\.*python\.exe)\s*$") {
            & $Matches[1] -m venv $venvDir
        } else {
            throw "Python Launcher did not report Python 3.11 or newer."
        }
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $venvDir
    } else {
        throw "Python was not found. Install Python 3.11 or newer."
    }
}

$requirements = Join-Path $backendDir "requirements.txt"
$requirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $requirements).Hash
$requirementsMarker = Join-Path $venvDir ".requirements.sha256"
$installedHash = if (Test-Path -LiteralPath $requirementsMarker) { (Get-Content -Raw -LiteralPath $requirementsMarker).Trim() } else { "" }
if ($installedHash -ne $requirementsHash) {
    Write-Host "Installing backend dependencies..."
    & $venvPython -m pip install --disable-pip-version-check -r $requirements
    $requirementsHash | Set-Content -Encoding ascii -LiteralPath $requirementsMarker
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    & $npm ci --prefix $frontendDir
}

$env:MODEL_PROVIDER = "mock"
$env:AUTH_MODE = "disabled"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
$backend = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru

$env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort/api"
$nodeCommand = (Get-Command node.exe -ErrorAction Stop).Source
$viteEntry = Join-Path $frontendDir "node_modules\vite\bin\vite.js"
$viteEntryArgument = "`"$viteEntry`""
$frontend = Start-Process -FilePath $nodeCommand `
    -ArgumentList $viteEntryArgument, "--host", "127.0.0.1", "--port", "$FrontendPort" `
    -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru

@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
    backend_port = $BackendPort
    frontend_port = $FrontendPort
    started_at = [DateTimeOffset]::Now.ToString("o")
} | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $pidFile

$healthy = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2
        if ($response.status -eq "ok") { $healthy = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $healthy) {
    Write-Warning "Backend health check failed. Run scripts\stop-demo.ps1 and check dependencies or port usage."
    exit 1
}

Write-Host ""
Write-Host "Lawyer Case Copilot is running." -ForegroundColor Green
Write-Host "Web: http://localhost:$FrontendPort"
Write-Host "API: http://localhost:$BackendPort/docs"
Write-Host "Stop: powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1"
if (-not $NoBrowser) { Start-Process "http://localhost:$FrontendPort" }
