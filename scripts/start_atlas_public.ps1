param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "ATLAS virtual environment not found at $Python. Create/restore .venv first."
}

$Cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $Cloudflared) {
    Write-Host "cloudflared is not installed." -ForegroundColor Yellow
    Write-Host "Install it in PowerShell with:" -ForegroundColor Yellow
    Write-Host "  winget install --id Cloudflare.cloudflared" -ForegroundColor Cyan
    exit 1
}

# Public launch is always read-only. Never enable live order execution from this launcher.
$env:ATLAS_LIVE_TRADING = "false"
$env:ATLAS_DASHBOARD_ONLY = "true"

$BaseUrl = "http://127.0.0.1:$Port"

Write-Host "Starting ATLAS read-only subscriber server..." -ForegroundColor Cyan
$Server = Start-Process -FilePath $Python -ArgumentList @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", "$Port"
) -WorkingDirectory $ProjectRoot -PassThru

try {
    $Healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $Response = Invoke-WebRequest "$BaseUrl/health" -UseBasicParsing -TimeoutSec 2
            if ($Response.StatusCode -eq 200) {
                $Healthy = $true
                break
            }
        } catch {
            # Keep polling during application startup.
        }
    }

    if (-not $Healthy) {
        throw "ATLAS did not become healthy at $BaseUrl/health."
    }

    Write-Host "ATLAS is healthy." -ForegroundColor Green
    Write-Host "Local subscribe: $BaseUrl/subscribe"
    Write-Host "Local Whish Money requests: $BaseUrl/billing/methods"
    Write-Host "Local dashboard: $BaseUrl/dashboard"
    Write-Host ""
    Write-Host "Starting Cloudflare Quick Tunnel..." -ForegroundColor Cyan
    Write-Host "Copy the https://...trycloudflare.com URL printed below." -ForegroundColor Yellow
    Write-Host "Subscriber links will be <tunnel>/subscribe and <tunnel>/dashboard." -ForegroundColor Yellow
    Write-Host ""

    & cloudflared tunnel --url $BaseUrl
}
finally {
    if ($Server -and -not $Server.HasExited) {
        Write-Host "Stopping ATLAS subscriber server..." -ForegroundColor Yellow
        Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
    }
}
