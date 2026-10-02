$ErrorActionPreference='Stop'
$env:ATLAS_BACKEND_ORIGIN='http://127.0.0.1:8012'
$env:ATLAS_BUILD_DIR='.next-owner-ops-20261003'
Set-Location $PSScriptRoot
& node.exe .\node_modules\next\dist\bin\next start --hostname 127.0.0.1 --port 8011
exit $LASTEXITCODE
