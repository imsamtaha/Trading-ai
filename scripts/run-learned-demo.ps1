$ErrorActionPreference = 'Stop'
$project = 'C:\Users\KHAT W TELEPHONE\Trading-ai-atlas-agent-v2'
$python = 'C:\Users\KHAT W TELEPHONE\Trading-ai\.venv\Scripts\python.exe'
$env:ATLAS_MT5_TICK_OFFSET_SECONDS = '10800'
$env:MT5_REQUIRE_DEMO = 'true'
$env:ATLAS_LIVE_TRADING = 'false'
$env:ATLAS_USER_REAL_ORDERS = 'false'
New-Item -ItemType Directory -Path "$project\var" -Force | Out-Null
Set-Location $project
& $python "$project\scripts\atlas_learned_demo_worker.py" *>> "$project\var\demo_worker.log"
exit $LASTEXITCODE
