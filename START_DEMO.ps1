$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Trading AI Demo Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1

Write-Host "Installing/updating requirements..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

$env:ATLAS_LIVE_TRADING = "false"
$env:ATLAS_DASHBOARD_ONLY = "true"

$Port = if ($env:ATLAS_DEMO_PORT) { $env:ATLAS_DEMO_PORT } else { "8010" }
$HostAddress = if ($env:ATLAS_DEMO_HOST) { $env:ATLAS_DEMO_HOST } else { "127.0.0.1" }

Write-Host ""
Write-Host "Starting ATLAS demo dashboard..." -ForegroundColor Green
Write-Host "Local URL: http://127.0.0.1:$Port/dashboard" -ForegroundColor Green

if ($HostAddress -eq "0.0.0.0") {
    Write-Host ""
    Write-Host "Sharing mode is enabled for your local Wi-Fi network." -ForegroundColor Yellow
    Write-Host "Find your IPv4 address with: ipconfig" -ForegroundColor Yellow
    Write-Host "Friends can open: http://YOUR_IPV4_ADDRESS:$Port/dashboard" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Execution mode: DISABLED" -ForegroundColor Red
Write-Host "Trading mode: live market-data demo + paper-trading candidate only" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host $HostAddress --port $Port --reload
