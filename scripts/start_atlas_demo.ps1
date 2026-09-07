[CmdletBinding()]
param(
    [switch]$Once,
    [switch]$NoDashboard,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python virtual environment was not found. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}
if (-not (Test-Path ".env")) {
    throw "Create .env from .env.mt5.example, then enter the MT5 demo credentials. Supabase is optional for local paper trading."
}

New-Item -ItemType Directory -Force (Join-Path $projectRoot "data") | Out-Null

# The forward-demo launcher always forces safe paper mode.
$env:ATLAS_LIVE_TRADING = "false"
$env:ATLAS_ENVIRONMENT = "paper"

& $python scripts\verify_mt5.py
if ($LASTEXITCODE -ne 0) {
    throw "MT5 is not connected. Keep the MT5 demo terminal open, then check .env values."
}

if (-not $NoDashboard) {
    $env:ATLAS_DASHBOARD_ONLY = "true"
    $baseUrl = "http://127.0.0.1:$Port"
    $healthy = $false
    try {
        $response = Invoke-WebRequest "$baseUrl/health" -UseBasicParsing -TimeoutSec 2
        $healthy = $response.StatusCode -eq 200
    } catch {
        $healthy = $false
    }

    if (-not $healthy) {
        Start-Process -FilePath $python -ArgumentList @(
            "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "$Port"
        ) -WorkingDirectory $projectRoot | Out-Null

        for ($attempt = 0; $attempt -lt 20; $attempt++) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest "$baseUrl/health" -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -eq 200) {
                    $healthy = $true
                    break
                }
            } catch {
                $healthy = $false
            }
        }
    }

    if (-not $healthy) {
        throw "ATLAS API did not become healthy on $baseUrl."
    }

    Write-Host "ATLAS dashboard: $baseUrl/dashboard" -ForegroundColor Green
}

Write-Host "Forward-demo monitor: PAPER ONLY; no MT5 orders." -ForegroundColor Cyan
Write-Host "Status command: .\.venv\Scripts\python.exe .\scripts\atlas_demo_status.py" -ForegroundColor Cyan

if ($Once) {
    & $python run_atlas_mt5.py --once
} else {
    & $python run_atlas_mt5.py
}

exit $LASTEXITCODE
