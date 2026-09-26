param(
    [int]$Port = 8000,
    [ValidateSet("quick", "named")]
    [string]$TunnelMode = "quick",
    [string]$TunnelName = "atlas",
    [string]$TunnelConfig = "$env:USERPROFILE\.cloudflared\config.yml",
    [string]$Hostname = "justai-atlas.online",
    [switch]$RepairDnsRoute
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
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
$env:ATLAS_APP_URL = "https://$Hostname"
$env:ATLAS_SUBSCRIPTION_PRICE = '$99 signals / $149 execution'
$env:ATLAS_SUBSCRIPTION_TRIAL = 'manual Whish approval'

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
    Write-Host "Local dashboard: $BaseUrl/dashboard"
    Write-Host "Whish subscriptions: $BaseUrl/subscribe"
    Write-Host ""
    if ($TunnelMode -eq "named") {
        if (-not (Test-Path -LiteralPath $TunnelConfig)) {
            throw "Named tunnel config was not found at $TunnelConfig. Use -TunnelMode quick for a temporary test, or install the named tunnel credentials."
        }

        $credentialsMatch = Select-String -LiteralPath $TunnelConfig -Pattern '^\s*credentials-file:\s*(.+)\s*$' -ErrorAction SilentlyContinue
        if (-not $credentialsMatch) {
            throw "Named tunnel config does not declare credentials-file: $TunnelConfig"
        }

        $credentialsPath = $credentialsMatch.Matches[0].Groups[1].Value.Trim().Trim('"')
        if (-not (Test-Path -LiteralPath $credentialsPath)) {
            throw "Named tunnel credentials were not found at $credentialsPath. Complete cloudflared login or install the tunnel credentials before using -TunnelMode named."
        }

        if ($RepairDnsRoute) {
            Write-Host "Repairing Cloudflare DNS route for $Hostname -> tunnel '$TunnelName'..." -ForegroundColor Cyan
            & cloudflared tunnel --config $TunnelConfig route dns $TunnelName $Hostname
            if ($LASTEXITCODE -ne 0) {
                throw "Cloudflare DNS route repair failed for $Hostname. Check Cloudflare login, zone ownership, and existing A/AAAA records."
            }
        }

        Write-Host "Starting named Cloudflare Tunnel '$TunnelName'..." -ForegroundColor Cyan
        & cloudflared tunnel --config $TunnelConfig run $TunnelName
    }
    else {
        # NUL prevents a user's named-tunnel config from being auto-loaded into
        # this accountless test tunnel. HTTP/2 is more reliable on Windows
        # networks that allow TCP but intermittently time out QUIC DNS lookups.
        Write-Host "Starting isolated Cloudflare Quick Tunnel..." -ForegroundColor Cyan
        Write-Host "Copy the https://...trycloudflare.com URL printed below." -ForegroundColor Yellow
        Write-Host "Subscriber links will be <tunnel>/subscribe and <tunnel>/dashboard." -ForegroundColor Yellow
        Write-Host ""

        & cloudflared tunnel --config NUL --protocol http2 --url $BaseUrl
    }
}
finally {
    if ($Server -and -not $Server.HasExited) {
        Write-Host "Stopping ATLAS subscriber server..." -ForegroundColor Yellow
        Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue
    }
}
