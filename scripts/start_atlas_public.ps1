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

Write-Host "Starting ATLAS ULTIMATE read-only server..." -ForegroundColor Cyan
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
        throw "ATLAS ULTIMATE did not become healthy at $BaseUrl/health."
    }

    Write-Host "ATLAS ULTIMATE is healthy." -ForegroundColor Green
    Write-Host "Local canonical address: $BaseUrl/" -ForegroundColor Green
    Write-Host "Production canonical address: https://justai-atlas.online/" -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting Cloudflare Quick Tunnel..." -ForegroundColor Cyan
    Write-Host "For temporary testing, share only the tunnel root URL." -ForegroundColor Yellow
    Write-Host "For production, share only https://justai-atlas.online/" -ForegroundColor Yellow
    Write-Host "Legacy paths remain compatibility redirects only and must not be advertised." -ForegroundColor DarkGray
    Write-Host ""

    & cloudflared tunnel --url $BaseUrl
}
finally {
    if ($Server -and -not $Server.HasExited) {
        Write-Host "Stopping ATLAS ULTIMATE server..." -ForegroundColor Yellow
        Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
    }
}
