[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
    [string]$ProjectId,

    [ValidatePattern("^[a-z]+-[a-z]+[0-9]+$")]
    [string]$Region = "europe-west1",

    [ValidatePattern("^[a-z][a-z0-9-]{0,48}$")]
    [string]$Service = "atlas-market",

    [ValidatePattern("^[a-z][a-z0-9-]{2,62}$")]
    [string]$Repository = "atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Gcloud {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud failed: gcloud $($Arguments -join ' ')"
    }
    return $output
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI is not installed. Install it, reopen PowerShell, then run this script again."
}

$activeAccount = (& gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>$null | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($activeAccount)) {
    throw "No active Google Cloud account. Run: gcloud auth login"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot

try {
    Write-Host "Using Google Cloud account: $activeAccount"
    Invoke-Gcloud -Arguments @("config", "set", "project", $ProjectId) | Out-Host

    $apis = @(
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com",
        "run.googleapis.com",
        "cloudresourcemanager.googleapis.com"
    )
    Invoke-Gcloud -Arguments (@("services", "enable") + $apis + @("--project", $ProjectId)) | Out-Host

    $describeArgs = @(
        "artifacts", "repositories", "describe", $Repository,
        "--location", $Region,
        "--project", $ProjectId,
        "--format=value(name)"
    )
    & gcloud @describeArgs 2>$null | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Invoke-Gcloud -Arguments @(
            "artifacts", "repositories", "create", $Repository,
            "--repository-format", "docker",
            "--location", $Region,
            "--description", "ATLAS Cloud Run images",
            "--project", $ProjectId,
            "--quiet"
        ) | Out-Host
    }
    else {
        Write-Host "Artifact Registry repository already exists: $Repository"
    }

    Invoke-Gcloud -Arguments @(
        "builds", "submit",
        "--config", "cloudbuild.yaml",
        "--region", $Region,
        "--project", $ProjectId,
        "--substitutions", "_REGION=$Region,_REPOSITORY=$Repository,_SERVICE=$Service",
        "."
    ) | Out-Host

    $serviceUrl = (
        Invoke-Gcloud -Arguments @(
            "run", "services", "describe", $Service,
            "--region", $Region,
            "--project", $ProjectId,
            "--format=value(status.url)"
        )
    ).Trim()

    if ([string]::IsNullOrWhiteSpace($serviceUrl) -or -not $serviceUrl.StartsWith("https://")) {
        throw "Cloud Run did not return a valid HTTPS service URL."
    }

    $health = Invoke-RestMethod -Method Get -Uri "$serviceUrl/health" -TimeoutSec 30
    if ($health.status -ne "healthy") {
        throw "Health verification failed. Expected status=healthy."
    }

    Write-Host ""
    Write-Host "ATLAS Cloud Run deployment is healthy."
    Write-Host "Service: $serviceUrl"
    Write-Host "Health:  $serviceUrl/health"
    Write-Host "Mode:    dashboard-only; live trading disabled"
}
finally {
    Pop-Location
}
