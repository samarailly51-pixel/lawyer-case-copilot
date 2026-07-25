[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pidFile = Join-Path $repoRoot ".demo-runtime\processes.json"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "No running demo was found."
    exit 0
}

$processes = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
foreach ($processId in @($processes.backend_pid, $processes.frontend_pid)) {
    if ($processId) {
        Stop-Process -Id $processId -ErrorAction SilentlyContinue
    }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Host "Lawyer Case Copilot Demo stopped." -ForegroundColor Green
