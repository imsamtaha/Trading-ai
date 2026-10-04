# Exercise the actual mode logic in a temporary checkout. Replace only external
# process/session functions, so no real MT5 session or server can be started.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$source = Get-Content (Join-Path $root 'ATLAS_SWITCH.ps1') -Raw
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'Switch parse failed' }
$replacements = @{
  'Get-MT5Mode' = 'function Get-MT5Mode { return 0 }'
  'Stop-AtlasProcesses' = 'function Stop-AtlasProcesses {}'
  'Start-DemoWorker' = 'function Start-DemoWorker { Set-Content (Join-Path $Root "worker-started.txt") "demo-only" }'
  'Start-Dashboard' = @'
function Start-Dashboard {
  $values = @{}
  foreach ($name in @('ATLAS_DASHBOARD_ONLY','ATLAS_EVOLUTION_WRITES_ENABLED','ATLAS_LIVE_TRADING','ATLAS_AUTO_EXECUTION_ENABLED','ATLAS_LIVE_DEMO','MT5_REQUIRE_DEMO','MT5_USE_ACTIVE_SESSION','ATLAS_DEMO_MAX_DAILY_ENTRIES','ATLAS_DEMO_MAX_OPEN_POSITIONS')) {
    $values[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }
  $values | ConvertTo-Json | Set-Content (Join-Path $Root 'spawned-env.json')
}
'@
}
$nodes = $ast.FindAll({param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $replacements.ContainsKey($node.Name)
}, $true) | Sort-Object { $_.Extent.StartOffset } -Descending
foreach ($node in $nodes) {
  $source = $source.Remove($node.Extent.StartOffset, $node.Extent.EndOffset - $node.Extent.StartOffset).Insert($node.Extent.StartOffset, $replacements[$node.Name])
}
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$inherited = @{}
foreach ($name in @('ATLAS_DASHBOARD_ONLY','ATLAS_LIVE_TRADING','ATLAS_AUTO_EXECUTION_ENABLED')) {
  $inherited[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  [Environment]::SetEnvironmentVariable($name, $(if ($name -eq 'ATLAS_DASHBOARD_ONLY') {'false'} else {'true'}), 'Process')
}
try {
  $script = Join-Path $tempRoot 'ATLAS_SWITCH.ps1'
  Set-Content $script $source -Encoding UTF8
  foreach ($mode in @('DEMO','DASHBOARD','OFF','DEMO_TRADE')) {
    Set-Content (Join-Path $tempRoot '.env') @(
      'ATLAS_DASHBOARD_ONLY=false', 'ATLAS_EVOLUTION_WRITES_ENABLED=true',
      'ATLAS_LIVE_TRADING=true', 'ATLAS_AUTO_EXECUTION_ENABLED=true'
    )
    & (Join-Path $PSHOME 'pwsh.exe') -NoProfile -File $script -Mode $mode -Evolution
    if ($LASTEXITCODE -ne 0) { throw "$mode switch failed" }
    $settings = @{}
    Get-Content (Join-Path $tempRoot '.env') | ForEach-Object {
      $parts = $_ -split '=',2
      $settings[$parts[0]] = $parts[1]
    }
    $expectedGuard = if ($mode -eq 'DASHBOARD') { 'false' } else { 'true' }
    if ($settings['ATLAS_DASHBOARD_ONLY'] -ne $expectedGuard) { throw "$mode write guard missing" }
    foreach ($name in @('ATLAS_LIVE_TRADING', 'ATLAS_AUTO_EXECUTION_ENABLED')) {
      $expected = if ($mode -eq 'DEMO_TRADE') { 'true' } else { 'false' }
      if ($settings[$name] -ne $expected) { throw "$mode unexpected execution state" }
    }
    if ($mode -ne 'OFF') {
      $spawned = Get-Content (Join-Path $tempRoot 'spawned-env.json') -Raw | ConvertFrom-Json
      foreach ($name in $settings.Keys) {
        if ($spawned.$name -ne $settings[$name]) { throw "$mode inherited stale process flag: $name" }
      }
    }
    if ($mode -eq 'DEMO' -and $settings['ATLAS_EVOLUTION_WRITES_ENABLED'] -ne 'false') {
      throw 'DEMO unexpectedly enabled evolution writes'
    }
    if ($mode -eq 'DEMO_TRADE') {
      if ($settings['MT5_REQUIRE_DEMO'] -ne 'true' -or $settings['MT5_USE_ACTIVE_SESSION'] -ne 'true') { throw 'Demo account boundary missing' }
      if ($settings['ATLAS_DEMO_MAX_DAILY_ENTRIES'] -ne '15' -or $settings['ATLAS_DEMO_MAX_OPEN_POSITIONS'] -ne '5') { throw 'Demo limits missing' }
      if ($settings['ATLAS_EVOLUTION_WRITES_ENABLED'] -ne 'false') { throw 'Demo trade enabled evolution writes' }
      if (-not (Test-Path (Join-Path $tempRoot 'worker-started.txt'))) { throw 'Demo worker was not requested' }
    }
  }
  Write-Host 'ATLAS switch mode isolation passed (external operations stubbed)'
} finally {
  foreach ($name in $inherited.Keys) { [Environment]::SetEnvironmentVariable($name, $inherited[$name], 'Process') }
  Remove-Item $tempRoot -Recurse -Force
}
