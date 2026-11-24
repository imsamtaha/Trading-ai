[CmdletBinding()]
param(
  [int]$Port = 8011,
  [int]$BackendPort = 8012,
  [string]$BuildDir = '.next-production'
)

$ErrorActionPreference = 'Stop'
$project = 'C:\Users\KHAT W TELEPHONE\ATLAS\runtime\web-ui'
if (-not (Test-Path (Join-Path $project 'node_modules\next\dist\bin\next'))) {
  throw 'ATLAS web dependencies are not installed.'
}

$env:ATLAS_BACKEND_ORIGIN = "http://127.0.0.1:$BackendPort"
$env:ATLAS_BUILD_DIR = $BuildDir
Set-Location $project
& node.exe '.\node_modules\next\dist\bin\next' start --hostname 127.0.0.1 --port $Port
exit $LASTEXITCODE
