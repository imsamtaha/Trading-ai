param(
    [switch]$SkipDocker,
    [switch]$SkipWeb,
    [switch]$SkipMT5,
    [string]$OutputDir = "artifacts"
)

$ErrorActionPreference = "Stop"
$env:ATLAS_LIVE_TRADING = 'false'
$env:MT5_REQUIRE_DEMO = 'true'
$env:ATLAS_DASHBOARD_ONLY = 'true'
$env:ATLAS_ENVIRONMENT = 'paper'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$logsDir = Join-Path $OutputDir "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$groups = [System.Collections.Generic.List[object]]::new()

function Add-AtlasResult {
    param(
        [string]$Name,
        [string]$Status,
        [bool]$Required,
        [double]$DurationSeconds,
        [string]$Reason = ""
    )
    $groups.Add([ordered]@{
        name = $Name
        status = $Status
        required = $Required
        duration_seconds = [math]::Round($DurationSeconds, 3)
        reason = $Reason
    })
}

function Invoke-AtlasCommandGroup {
    param(
        [string]$Name,
        [string[]]$Commands,
        [bool]$Required = $true
    )
    $started = Get-Date
    $logPath = Join-Path $logsDir "$Name.log"
    try {
        foreach ($command in $Commands) {
            "`n>>> $command" | Out-File -FilePath $logPath -Append -Encoding utf8
            & pwsh -NoProfile -Command $command *>> $logPath
            if ($LASTEXITCODE -ne 0) {
                throw "$Name command failed with exit code $LASTEXITCODE"
            }
        }
        Add-AtlasResult $Name "PASS" $Required ((Get-Date) - $started).TotalSeconds
        return $true
    }
    catch {
        Add-AtlasResult $Name "FAIL" $Required ((Get-Date) - $started).TotalSeconds $_.Exception.Message
        return $false
    }
}

# repo_tests
Invoke-AtlasCommandGroup "repo_tests" @(
    'python -m pytest -q'
) $true | Out-Null

# web_tests
if ($SkipWeb) {
    Add-AtlasResult "web_tests" "NOT_RUN" $false 0 "Skipped by -SkipWeb"
}
else {
    Invoke-AtlasCommandGroup "web_tests" @(
        'node --check web/assets/site.js',
        'node --test tests/test_demo_model.cjs',
        'node --test tests/test_google_auth.mjs',
        'node --check web/assets/google-auth.js',
        'python scripts/build_website.py'
    ) $true | Out-Null
}

# risk_safety
Invoke-AtlasCommandGroup "risk_safety" @(
    'python -m pytest tests/test_atlas_risk_management_v2.py tests/test_execution.py tests/test_atlas_agent_paper_gate.py tests/test_demo_operations.py -q'
) $true | Out-Null

# windows_integrity
if ($IsWindows) {
    Invoke-AtlasCommandGroup "windows_integrity" @(
        '$source = Get-Content scripts/deploy_google_cloud.ps1 -Raw; $null = [scriptblock]::Create($source)',
        'python -m pytest tests/test_signal_journal_integrity.py tests/test_atlas_demo_status_integrity.py -q'
    ) $true | Out-Null
}
else {
    Add-AtlasResult "windows_integrity" "NOT_RUN" $false 0 "Windows-only integrity stage"
}

# api_smoke / Docker: /health must be 200 and /mt5/test-order must remain 403.
if ($SkipDocker) {
    Add-AtlasResult "api_smoke" "NOT_RUN" $false 0 "Skipped by -SkipDocker"
}
elseif (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Add-AtlasResult "api_smoke" "NOT_RUN" $false 0 "Docker is unavailable"
}
else {
    $started = Get-Date
    $containerName = "atlas-full-test-$PID"
    $logPath = Join-Path $logsDir "api_smoke.log"
    try {
        docker build --tag atlas-full-test . *>> $logPath
        if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
        docker run --detach --name $containerName --publish 127.0.0.1:18080:8080 --env PORT=8080 --env ATLAS_DASHBOARD_ONLY=true --env ATLAS_PUBLIC_ANALYSIS_ENABLED=false --env ATLAS_LIVE_TRADING=false atlas-full-test *>> $logPath
        if ($LASTEXITCODE -ne 0) { throw "Docker run failed" }
        $healthy = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $health = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18080/health' -TimeoutSec 2
                if ($health.StatusCode -eq 200) { $healthy = $true; break }
            }
            catch {
                Start-Sleep -Seconds 1
            }
        }
        if (-not $healthy) { throw "/health did not return 200" }
        try {
            $null = Invoke-WebRequest -UseBasicParsing -Method POST -Uri 'http://127.0.0.1:18080/mt5/test-order' -TimeoutSec 5
            throw "/mt5/test-order unexpectedly accepted a request"
        }
        catch {
            $status = [int]$_.Exception.Response.StatusCode
            if ($status -ne 403) { throw "Expected /mt5/test-order 403, received $status" }
        }
        Add-AtlasResult "api_smoke" "PASS" $true ((Get-Date) - $started).TotalSeconds
    }
    catch {
        Add-AtlasResult "api_smoke" "FAIL" $true ((Get-Date) - $started).TotalSeconds $_.Exception.Message
    }
    finally {
        docker rm --force $containerName 2>$null | Out-Null
    }
}

# mt5_demo_runtime: existing broker config enforces DEMO because MT5_REQUIRE_DEMO=true.
if ($SkipMT5) {
    Add-AtlasResult "mt5_demo_runtime" "NOT_RUN" $false 0 "Skipped by -SkipMT5"
}
elseif (-not $IsWindows) {
    Add-AtlasResult "mt5_demo_runtime" "NOT_RUN" $false 0 "MT5 runtime requires Windows"
}
else {
    $mt5Available = $false
    try {
        python -c "import MetaTrader5" 2>$null
        $mt5Available = ($LASTEXITCODE -eq 0)
    }
    catch {
        $mt5Available = $false
    }

    if (-not $mt5Available) {
        Add-AtlasResult "mt5_demo_runtime" "NOT_RUN" $false 0 "MetaTrader5 Python package is unavailable"
    }
    elseif (-not $env:MT5_LOGIN -or -not $env:MT5_SERVER) {
        Add-AtlasResult "mt5_demo_runtime" "NOT_RUN" $false 0 "MT5 demo credentials/configuration are unavailable"
    }
    else {
        Invoke-AtlasCommandGroup "mt5_demo_runtime" @(
            'python scripts/verify_mt5.py',
            'python run_atlas_mt5.py --once'
        ) $false | Out-Null
    }
}

# restart_reconnect: never claim PASS unless a deterministic duplicate/reconnect contract exists.
$restartTest = 'tests/test_mt5_restart_reconnect.py'
if (Test-Path $restartTest) {
    Invoke-AtlasCommandGroup "restart_reconnect" @(
        "python -m pytest $restartTest -q"
    ) $false | Out-Null
}
else {
    Add-AtlasResult "restart_reconnect" "PARTIAL" $false 0 "No deterministic restart/reconnect idempotency contract exists yet"
}

$groupsPath = Join-Path $OutputDir "atlas_test_groups.json"
$groups | ConvertTo-Json -Depth 8 | Set-Content -Path $groupsPath -Encoding utf8
$commitSha = (git rev-parse HEAD).Trim()
$pythonCode = @'
import json, sys
from scripts.atlas_test_report import build_report, write_report
with open(sys.argv[1], encoding="utf-8-sig") as handle:
    groups = json.load(handle)
report = build_report(sys.argv[2], groups)
paths = write_report(report, sys.argv[3])
print(report["overall"])
print(paths[0])
print(paths[1])
raise SystemExit(1 if report["overall"] == "FAIL" else 0)
'@
$pythonCode | python - $groupsPath $commitSha $OutputDir
exit $LASTEXITCODE
