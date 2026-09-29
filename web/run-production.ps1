$ErrorActionPreference = 'Stop'
$env:ATLAS_BACKEND_ORIGIN = 'http://127.0.0.1:8012'
$env:ATLAS_BUILD_DIR = '.next-release4'
Set-Location $PSScriptRoot
& npm.cmd run start -- --hostname 127.0.0.1 --port 8011
