[CmdletBinding()]
param(
    [string]$RepositoryPath = '',
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([string]::IsNullOrWhiteSpace($RepositoryPath)) { $RepositoryPath = $PSScriptRoot }

# This installer validates the checked-out files. Source changes belong in Git;
# it never reconstructs embedded source or stages, commits, pushes, or starts MT5.
$repo = (Resolve-Path -LiteralPath $RepositoryPath).Path
$scriptRootResolved = (Resolve-Path -LiteralPath $PSScriptRoot).Path
if ($repo -ne $scriptRootResolved) { throw 'Run the installer from the intended checkout.' }
$gitRoot = & git -C $repo rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'Unable to verify repository root.' }
if ((Resolve-Path -LiteralPath $gitRoot).Path -ne $repo) { throw 'Installer must reside at the repository root.' }
foreach ($relative in @('config/council_role_thresholds.json', 'src/council/consensus_aggregator.py', 'tests/test_council_consensus_safety.py', 'tests/test_council_observed_calibration.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo $relative) -PathType Leaf)) { throw "Required file missing: $relative" }
}
$safety = @{
    ATLAS_LIVE_TRADING='false'; ATLAS_DASHBOARD_ONLY='true';
    ATLAS_AGENT_PAPER_EXECUTION_ENABLED='false'; MT5_REQUIRE_DEMO='true';
    ATLAS_ENVIRONMENT='paper'; ATLAS_CI_DRY_RUN='true'; MT5_READONLY_MODE='true'
}
$previous = @{}
try {
    foreach ($key in $safety.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $safety[$key], 'Process')
    }
    Push-Location -LiteralPath $repo
    try {
        & $Python 'src/council/consensus_aggregator.py'
        if ($LASTEXITCODE -ne 0) { throw 'Council policy validation failed.' }
        $testParent = Join-Path $repo 'data/council-validation'
        New-Item -ItemType Directory -Force -Path $testParent | Out-Null
        $testTemp = Join-Path $testParent ([Guid]::NewGuid().ToString('N'))
        & $Python -m pytest tests/test_council_consensus_safety.py tests/test_council_observed_calibration.py -q --basetemp $testTemp
        if ($LASTEXITCODE -ne 0) { throw 'Council safety tests failed.' }
    } finally { Pop-Location }
} finally {
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
}
Write-Host 'ATLAS Council PAPER validation completed successfully. Broker execution remains disabled.' -ForegroundColor Green
