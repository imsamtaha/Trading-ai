[CmdletBinding()]
param([switch]$Once)

$ErrorActionPreference = 'Stop'
$project = 'C:\Users\KHAT W TELEPHONE\ATLAS'
$python = 'C:\Users\KHAT W TELEPHONE\ATLAS\.venv\Scripts\python.exe'
$sourceEnv = 'C:\Users\KHAT W TELEPHONE\ATLAS\.runtime\config\atlas-runtime.env'
$stateDir = 'C:\Users\KHAT W TELEPHONE\ATLAS\.runtime\paper'

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

# Load only the optional persistence credentials needed by the paper monitor.
if (Test-Path $sourceEnv) {
    Get-Content $sourceEnv | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $parts = $line.Split('=', 2)
            $name = $parts[0].Trim()
            if ($name -in @('SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY')) {
                [Environment]::SetEnvironmentVariable($name, $parts[1].Trim(), 'Process')
            }
        }
    }
}

# Hard safety boundary: quotes may come from MT5, orders never do.
$env:ATLAS_LIVE_TRADING = 'false'
$env:ATLAS_ENVIRONMENT = 'paper'
$env:MT5_REQUIRE_DEMO = 'true'
$env:MT5_USE_ACTIVE_SESSION = 'true'
$env:MT5_TERMINAL_PATH = 'C:\Program Files\FxPro Markets MT5\terminal64.exe'

# Paper portfolio limits.
$env:ATLAS_DEMO_MAX_DAILY_ENTRIES = '100'
$env:ATLAS_DEMO_MAX_OPEN_POSITIONS = '5'
$env:ATLAS_DEMO_LEDGER = Join-Path $stateDir 'atlas_demo_ledger.json'

# Council learns only from settled Paper outcomes.
$env:ATLAS_COUNCIL_TRAINING_ENABLED = 'true'
$env:ATLAS_COUNCIL_TRAINING_JOURNAL = Join-Path $stateDir 'atlas_council_training.jsonl'
$env:ATLAS_COUNCIL_PROFILE = Join-Path $stateDir 'atlas_council_profile.json'

$env:ATLAS_MT5_QUOTE_TIME_OFFSET_SECONDS = '10800'
$env:ATLAS_CYCLE_SECONDS = '30'
$env:ATLAS_MONITOR_TOP_N = '30'
$env:ATLAS_AUTO_DISCOVER_SYMBOLS = 'true'
$env:ATLAS_EXPANDED_DISCOVERY = 'true'
$env:ATLAS_CATEGORY_POSITION_LIMIT = '2'
$env:ATLAS_SHADOW_TRAINING_ENABLED = 'true'
$env:ATLAS_TRAINING_ACCELERATOR_ENABLED = 'true'
$env:ATLAS_NODE_EXE = 'C:\Program Files\nodejs\node.exe'
$env:ATLAS_SHADOW_REPORT = Join-Path $stateDir 'atlas_shadow_report.json'
$env:ATLAS_SHADOW_JOURNAL = Join-Path $stateDir 'atlas_shadow_predictions.jsonl'
$env:ATLAS_PERSIST_ALL_SIGNALS = 'false'

Set-Location $project
if ($Once) {
    & $python 'run_atlas_mt5.py' --once
} else {
    & $python 'run_atlas_mt5.py' *>> (Join-Path $stateDir 'paper-monitor.log')
}
exit $LASTEXITCODE
