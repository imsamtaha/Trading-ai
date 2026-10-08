[CmdletBinding()]
param([int]$Port = 8012)

$ErrorActionPreference = 'Stop'
$project = 'C:\Users\KHAT W TELEPHONE\ATLAS\runtime\private-api'
$python = 'C:\Users\KHAT W TELEPHONE\ATLAS\.venv\Scripts\python.exe'
$envFile = 'C:\Users\KHAT W TELEPHONE\ATLAS\.runtime\config\atlas-runtime.env'

if (-not (Test-Path $python)) { throw 'ATLAS Python environment is not installed.' }
if (-not (Test-Path $project)) { throw 'ATLAS private API runtime is missing.' }

if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
      $parts = $line.Split('=', 2)
      [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
    }
  }
}

# Runtime safety boundary. These values override any legacy config file values.
$env:ATLAS_LIVE_TRADING = 'false'
$env:ATLAS_DASHBOARD_ONLY = 'true'
$env:MT5_REQUIRE_DEMO = 'true'
$env:ATLAS_USER_DEMO_ORDERS = 'false'
$env:ATLAS_USER_REAL_ORDERS = 'false'
$env:ATLAS_AGENT_PAPER_EXECUTION_ENABLED = 'false'
$env:ATLAS_TRADE_AUDIT_DB = 'C:\Users\KHAT W TELEPHONE\ATLAS\.runtime\manual_mt5_orders.sqlite3'
$env:ATLAS_MEMORY_DB = 'C:\Users\KHAT W TELEPHONE\ATLAS\.runtime\atlas_memory.sqlite3'
$env:MT5_TERMINAL_PATH = 'C:\Program Files\FxPro Markets MT5\terminal64.exe'
$env:ATLAS_COUNCIL_MT5_TERMINAL_PATH = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$env:ATLAS_COUNCIL_MT5_SERVER = 'FxPro-MT5 Demo'

Set-Location $project
& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
