param(
  [ValidateSet("STATUS","OFF","DASHBOARD","DEMO")]
  [string]$Mode = "STATUS",
  [string]$Symbol = "EURUSD",
  [switch]$Evolution
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $Root ".env"
$Python = "C:\Users\KHAT W TELEPHONE\Trading-ai\.venv\Scripts\python.exe"

function Set-EnvValue([string]$Name, [string]$Value) {
  $lines = @()
  if (Test-Path $EnvFile) { $lines = Get-Content $EnvFile }
  $found = $false
  $updated = foreach ($line in $lines) {
    if ($line -match "^$([regex]::Escape($Name))=") {
      $found = $true
      "$Name=$Value"
    } else { $line }
  }
  if (-not $found) { $updated += "$Name=$Value" }
  Set-Content -Path $EnvFile -Value $updated -Encoding UTF8
}
function Get-MT5Mode {
  $code = @"
import MetaTrader5 as mt5
path=r'C:\Program Files\FxPro Markets MT5\terminal64.exe'
ok=mt5.initialize(path)
if not ok:
    print(-1)
else:
    a=mt5.account_info()
    print(-1 if a is None else int(a.trade_mode))
    mt5.shutdown()
"@
  $value = & $Python -c $code 2>$null
  return [int]($value | Select-Object -Last 1)
}

function Stop-AtlasProcesses {
  Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "uvicorn app.main:app|atlas_auto_execution.py"
  } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
}
function Start-Dashboard {
  $cmd = "Set-Location '$Root'; & '$Python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  Start-Process powershell -ArgumentList "-NoExit","-Command",$cmd
}

if ($Mode -eq "STATUS") {
  $names = @(
    "ATLAS_DASHBOARD_ONLY","ATLAS_LIVE_DEMO","ATLAS_LIVE_TRADING",
    "ATLAS_AUTO_EXECUTION_ENABLED","ATLAS_EVOLUTION_WRITES_ENABLED",
    "MT5_REQUIRE_DEMO","MT5_USE_ACTIVE_SESSION"
  )
  foreach ($name in $names) {
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^$name=" } | Select-Object -Last 1
    if ($line) { Write-Host $line } else { Write-Host "$name=<unset>" }
  }
  Write-Host "MT5 trade_mode: $(Get-MT5Mode)  (0=Demo, 2=Real)"
  exit 0
}
Stop-AtlasProcesses

if ($Mode -eq "OFF") {
  Set-EnvValue "ATLAS_LIVE_TRADING" "false"
  Set-EnvValue "ATLAS_AUTO_EXECUTION_ENABLED" "false"
  Set-EnvValue "ATLAS_EVOLUTION_WRITES_ENABLED" "false"
  Write-Host "ATLAS execution is OFF."
  exit 0
}

Set-EnvValue "ATLAS_DASHBOARD_ONLY" "false"
Set-EnvValue "ATLAS_EVOLUTION_WRITES_ENABLED" ($(if($Evolution){"true"}else{"false"}))

if ($Mode -eq "DASHBOARD") {
  Set-EnvValue "ATLAS_LIVE_TRADING" "false"
  Set-EnvValue "ATLAS_AUTO_EXECUTION_ENABLED" "false"
  Start-Dashboard
  Write-Host "ATLAS dashboard/backend started on http://127.0.0.1:8000"
  exit 0
}

$mt5Mode = Get-MT5Mode
if ($Mode -eq "DEMO") {
  if ($mt5Mode -ne 0) { throw "DEMO refused: active MT5 account is not Demo." }
  Set-EnvValue "MT5_REQUIRE_DEMO" "true"
  Set-EnvValue "MT5_USE_ACTIVE_SESSION" "true"
  Set-EnvValue "ATLAS_LIVE_DEMO" "true"
  Set-EnvValue "ATLAS_LIVE_TRADING" "false"
  Set-EnvValue "ATLAS_AUTO_EXECUTION_ENABLED" "false"
  Start-Dashboard
  Write-Host "ATLAS Demo mode active. Broker orders remain disabled."
  exit 0
}
