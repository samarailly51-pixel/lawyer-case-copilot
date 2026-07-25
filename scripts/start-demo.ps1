[CmdletBinding()]
param(
    [switch]$NoBrowser
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

if (Test-Path -LiteralPath $pidFile) {
    $existing = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
    $backendRunning = Get-Process -Id $existing.backend_pid -ErrorAction SilentlyContinue
    $frontendRunning = Get-Process -Id $existing.frontend_pid -ErrorAction SilentlyContinue
    if ($backendRunning -and $frontendRunning) {
        Write-Host "Demo is already running: http://localhost:5173" -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process "http://localhost:5173" }
        exit 0
    }
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
$backend = Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru

$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source
$frontend = Start-Process -FilePath $npmCommand `
    -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173" `
    -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru

@{
    backend_pid = $backend.Id
    frontend_pid = $frontend.Id
    started_at = [DateTimeOffset]::Now.ToString("o")
} | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $pidFile

$healthy = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
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
Write-Host "Web: http://localhost:5173"
Write-Host "API: http://localhost:8000/docs"
Write-Host "Stop: powershell -ExecutionPolicy Bypass -File scripts\stop-demo.ps1"
if (-not $NoBrowser) { Start-Process "http://localhost:5173" }
