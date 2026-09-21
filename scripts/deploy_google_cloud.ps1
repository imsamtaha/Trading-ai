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
    [string]$Repository = "atlas",

    [ValidatePattern("^[a-z0-9]{6,12}$")]
    [string]$IdentitySuffix = ([Guid]::NewGuid().ToString("N").Substring(0, 8))
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

function New-ServiceAccount {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AccountId,

        [Parameter(Mandatory = $true)]
        [string]$Email,

        [Parameter(Mandatory = $true)]
        [string]$DisplayName,

        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & gcloud iam service-accounts describe $Email --project $ProjectId 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        throw "Refusing to reuse existing service account: $Email"
    }

    Invoke-Gcloud -Arguments @(
        "iam", "service-accounts", "create", $AccountId,
        "--display-name", $DisplayName,
        "--description", $Description,
        "--project", $ProjectId,
        "--quiet"
    ) | Out-Host
}

function Get-ServiceAccountProjectRoles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Email
    )

    $roleOutput = Invoke-Gcloud -Arguments @(
        "projects", "get-iam-policy", $ProjectId,
        "--flatten=bindings[].members",
        "--filter=bindings.members=serviceAccount:$Email",
        "--format=value(bindings.role)"
    )

    return @(
        $roleOutput |
            ForEach-Object { ([string]$_).Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
}

function Assert-AllowedProjectRoles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Email,

        [string[]]$AllowedRoles = @()
    )

    $projectRoles = @(Get-ServiceAccountProjectRoles -Email $Email)
    $unexpectedRoles = @($projectRoles | Where-Object { $_ -notin $AllowedRoles })
    if ($unexpectedRoles.Count -gt 0) {
        throw "Unexpected project IAM roles on $($Email): $($unexpectedRoles -join ', ')"
    }
}

function Wait-AtlasHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [int]$Attempts = 10
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $health = Invoke-RestMethod -Method Get -Uri "$Url/health" -TimeoutSec 30
            if ($health.status -eq "healthy") {
                return $health
            }
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw
            }
        }

        if ($attempt -lt $Attempts) {
            Start-Sleep -Seconds ([Math]::Min($attempt, 5))
        }
    }

    throw "Health verification failed for $Url. Expected status=healthy."
}

function Get-HttpStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Method Post -Uri $Url -UseBasicParsing -TimeoutSec 30
        return [int]$response.StatusCode
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        throw
    }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "Google Cloud CLI is not installed. Install it, reopen PowerShell, then run this script again."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or is not available in PATH."
}

$activeAccount = (& gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>$null | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($activeAccount)) {
    throw "No active Google Cloud account. Run: gcloud auth login"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot

try {
    $workingTreeChanges = (& git status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect the Git working tree."
    }
    if ($workingTreeChanges) {
        throw "The Git working tree is not clean. Commit or stash changes before deployment."
    }

    $sourceRevision = (& git rev-parse HEAD).Trim().ToLowerInvariant()
    if ($LASTEXITCODE -ne 0 -or $sourceRevision -notmatch "^[0-9a-f]{40}$") {
        throw "Unable to resolve a full Git source revision."
    }

    Write-Host "Using Google Cloud account: $activeAccount"
    Write-Host "Project: $ProjectId"
    Write-Host "Source revision: $sourceRevision"

    $apis = @(
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com",
        "iam.googleapis.com",
        "run.googleapis.com",
        "cloudresourcemanager.googleapis.com"
    )
    Invoke-Gcloud -Arguments (@("services", "enable") + $apis + @("--project", $ProjectId)) | Out-Host

    $describeRepository = @(
        "artifacts", "repositories", "describe", $Repository,
        "--location", $Region,
        "--project", $ProjectId,
        "--format=value(name)"
    )
    & gcloud @describeRepository 2>$null | Out-Null

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

    $RuntimeServiceAccount = "atlas-run-$IdentitySuffix"
    $BuildServiceAccount = "atlas-build-$IdentitySuffix"
    $runtimeIdentity = "$RuntimeServiceAccount@$ProjectId.iam.gserviceaccount.com"
    $buildIdentity = "$BuildServiceAccount@$ProjectId.iam.gserviceaccount.com"
    $buildResource = "projects/$ProjectId/serviceAccounts/$buildIdentity"

    New-ServiceAccount -AccountId $RuntimeServiceAccount -Email $runtimeIdentity -DisplayName "ATLAS Cloud Run runtime" -Description "Runtime-only identity for ATLAS Cloud Run release $sourceRevision"
    New-ServiceAccount -AccountId $BuildServiceAccount -Email $buildIdentity -DisplayName "ATLAS Cloud Build worker" -Description "Build-only identity for ATLAS release $sourceRevision"

    Assert-AllowedProjectRoles -Email $runtimeIdentity
    Assert-AllowedProjectRoles -Email $buildIdentity -AllowedRoles @("roles/logging.logWriter")

    Invoke-Gcloud -Arguments @(
        "projects", "add-iam-policy-binding", $ProjectId,
        "--member", "serviceAccount:$buildIdentity",
        "--role", "roles/logging.logWriter",
        "--condition=None",
        "--quiet"
    ) | Out-Host
    Invoke-Gcloud -Arguments @(
        "artifacts", "repositories", "add-iam-policy-binding", $Repository,
        "--location", $Region,
        "--project", $ProjectId,
        "--member", "serviceAccount:$buildIdentity",
        "--role", "roles/artifactregistry.writer",
        "--condition=None",
        "--quiet"
    ) | Out-Host

    $existingServiceJson = & gcloud run services describe $Service --region $Region --project $ProjectId --format=json 2>$null
    if ($LASTEXITCODE -eq 0) {
        $existingService = ($existingServiceJson -join [Environment]::NewLine) | ConvertFrom-Json
        $existingContainers = @($existingService.spec.template.spec.containers)
        if ($existingContainers.Count -gt 1) {
            throw "Existing Cloud Run service has more than one container. Refusing to inherit or remove an unreviewed sidecar."
        }
    }

    $imageUri = "$($Region)-docker.pkg.dev/$ProjectId/$Repository/$($Service):$sourceRevision"
    Invoke-Gcloud -Arguments @(
        "builds", "submit",
        "--config", "cloudbuild.yaml",
        "--region", $Region,
        "--project", $ProjectId,
        "--service-account", $buildResource,
        "--substitutions", "_REGION=$Region,_REPOSITORY=$Repository,_SERVICE=$Service,_SOURCE_REVISION=$sourceRevision,_BUILD_SERVICE_ACCOUNT=$BuildServiceAccount",
        "."
    ) | Out-Host

    $candidateTag = "candidate-$($sourceRevision.Substring(0, 12))"
    Invoke-Gcloud -Arguments @(
        "run", "deploy", $Service,
        "--image", $imageUri,
        "--region", $Region,
        "--project", $ProjectId,
        "--platform", "managed",
        "--allow-unauthenticated",
        "--ingress", "all",
        "--port", "8080",
        "--cpu", "1",
        "--memory", "512Mi",
        "--concurrency", "40",
        "--min-instances", "0",
        "--max-instances", "3",
        "--timeout", "60",
        "--service-account", $runtimeIdentity,
        "--no-traffic",
        "--tag", $candidateTag,
        "--clear-secrets",
        "--clear-volumes",
        "--clear-volume-mounts",
        "--clear-cloudsql-instances",
        "--clear-vpc-connector",
        "--clear-network",
        "--clear-network-tags",
        "--set-env-vars", "ATLAS_LIVE_TRADING=false,ATLAS_DASHBOARD_ONLY=true,ATLAS_AGENT_PAPER_EXECUTION_ENABLED=false,ATLAS_PUBLIC_ANALYSIS_ENABLED=false,ATLAS_WHISH_ENABLED=true,ATLAS_WHISH_RECIPIENT=76420910,ATLAS_WHISH_SUPPORT=info@justai-atlas.online",
        "--labels", "source-revision=$sourceRevision,managed-by=atlas-deploy-script",
        "--quiet"
    ) | Out-Host

    $serviceStateJson = Invoke-Gcloud -Arguments @(
        "run", "services", "describe", $Service,
        "--region", $Region,
        "--project", $ProjectId,
        "--format=json"
    )
    $serviceState = ($serviceStateJson -join [Environment]::NewLine) | ConvertFrom-Json
    $candidateTraffic = $serviceState.status.traffic |
        Where-Object { $_.tag -eq $candidateTag } |
        Select-Object -First 1
    $candidateUrl = [string]$candidateTraffic.url

    if ([string]::IsNullOrWhiteSpace($candidateUrl) -or -not $candidateUrl.StartsWith("https://")) {
        throw "Cloud Run did not return a valid HTTPS URL for candidate tag $candidateTag."
    }

    $candidateHealth = Wait-AtlasHealth -Url $candidateUrl
    $StatusCode = Get-HttpStatus -Url "$candidateUrl/mt5/test-order"
    if ($StatusCode -ne 403) {
        throw "Candidate safety verification failed. Expected POST /mt5/test-order to return 403, received $StatusCode."
    }

    Invoke-Gcloud -Arguments @(
        "run", "services", "update-traffic", $Service,
        "--region", $Region,
        "--project", $ProjectId,
        "--to-tags", "$candidateTag=100",
        "--quiet"
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

    $health = Wait-AtlasHealth -Url $serviceUrl

    Write-Host ""
    Write-Host "ATLAS Cloud Run deployment is healthy."
    Write-Host "Service:          $serviceUrl"
    Write-Host "Candidate:        $candidateUrl"
    Write-Host "Health:           $serviceUrl/health"
    Write-Host "Source revision:  $sourceRevision"
    Write-Host "Runtime identity: $runtimeIdentity"
    Write-Host "Build identity:   $buildIdentity"
    Write-Host "Mode:             public read-only; trading, paper writes, and public analysis POSTs disabled"
}
finally {
    Pop-Location
}
