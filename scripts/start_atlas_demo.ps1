[CmdletBinding()]
param(
    [switch]$Once
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python virtual environment was not found. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}
if (-not (Test-Path ".env")) {
    throw "Create .env from .env.mt5.example, then enter the MT5 demo credentials and Supabase server values."
}

# These session values are deliberately forced even if .env contains something else.
$env:ATLAS_LIVE_TRADING = "false"
$env:ATLAS_DASHBOARD_ONLY = "true"
$env:ATLAS_ENVIRONMENT = "paper"

& $python scripts\verify_mt5.py
if ($LASTEXITCODE -ne 0) {
    throw "MT5 is not connected. Keep the MT5 demo terminal open, then check .env values."
}

if ($Once) {
    & $python run_atlas_mt5.py --once
} else {
    & $python run_atlas_mt5.py
}

exit $LASTEXITCODE
