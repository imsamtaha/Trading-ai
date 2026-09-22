[CmdletBinding()]
param([int]$Port = 8000, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$statePath = Join-Path $projectRoot 'data\session-processes.json'
New-Item -ItemType Directory -Force (Join-Path $projectRoot 'data') | Out-Null
function OwnedProcess($processId, $module, $expectedExecutable = $pythonPath) {
    if (-not $expectedExecutable) { $expectedExecutable = $pythonPath }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    return $process -and $process.ExecutablePath -eq $expectedExecutable -and $process.CommandLine.Contains($module)
}
function StopOwnedProcess($processId, $module, $expectedExecutable = $pythonPath) {
    if (-not $expectedExecutable) { $expectedExecutable = $pythonPath }
    if (OwnedProcess $processId $module $expectedExecutable) {
        # Windows venv launchers create a Python child; stop the owned tree too.
        & taskkill.exe /PID $processId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not stop ATLAS process $processId" }
    }
}
function ResolveDashboardProcess($port, $launcherId) {
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($listener) {
            $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
            if ($process -and (
                $process.ProcessId -eq $launcherId -or $process.ParentProcessId -eq $launcherId
            ) -and $process.CommandLine.Contains('uvicorn') -and $process.CommandLine.Contains("--port $port")) {
                return $process
            }
        }
        Start-Sleep -Milliseconds 200
    }
    throw "ATLAS dashboard did not bind to port $port with an owned process."
}
$saved = if (Test-Path -LiteralPath $statePath) { Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } else { $null }
if ($Stop) {
    if ($saved) {
        StopOwnedProcess $saved.worker 'app.monitor.demo_session' $saved.worker_executable
        StopOwnedProcess $saved.dashboard 'uvicorn' $saved.dashboard_executable
    }
    Write-Host 'ATLAS session processes stopped. MT5 terminal and ledger retained.'
    exit 0
}
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install requirements.txt first.' }
if ($saved -and (OwnedProcess $saved.worker 'app.monitor.demo_session' $saved.worker_executable) -and (OwnedProcess $saved.dashboard 'uvicorn' $saved.dashboard_executable)) {
    Write-Host "ATLAS session already running: http://127.0.0.1:$($saved.port)/dashboard"
    exit 0
}
# Never overwrite the process record for a partial session or occupy another service's port.
if ($saved -and ((OwnedProcess $saved.worker 'app.monitor.demo_session' $saved.worker_executable) -or (OwnedProcess $saved.dashboard 'uvicorn' $saved.dashboard_executable))) {
    throw 'Partial session detected. Run this script with -Stop, then start again.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is occupied. Choose -Port with a free port." }
$env:ATLAS_LIVE_TRADING='false'
$env:ATLAS_LIVE_DEMO='true'
$env:ATLAS_DASHBOARD_ONLY='true'
$env:ATLAS_AGENT_PAPER_EXECUTION_ENABLED='true'
$env:MT5_REQUIRE_DEMO='true'
$env:ATLAS_ENVIRONMENT='paper'
$server = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'data\dashboard.log') -RedirectStandardError (Join-Path $projectRoot 'data\dashboard-errors.log')
try {
    $dashboard = ResolveDashboardProcess $Port $server.Id
    $worker = Start-Process -FilePath $pythonPath -ArgumentList @('-m','app.monitor.demo_session') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'data\demo-worker.log') -RedirectStandardError (Join-Path $projectRoot 'data\demo-worker-errors.log')
    $workerProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($worker.Id)"
    @{
        dashboard=$dashboard.ProcessId
        dashboard_executable=$dashboard.ExecutablePath
        worker=$worker.Id
        worker_executable=$workerProcess.ExecutablePath
        port=$Port
    } | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8
} catch {
    if ($dashboard) { StopOwnedProcess $dashboard.ProcessId 'uvicorn' $dashboard.ExecutablePath }
    else { StopOwnedProcess $server.Id 'uvicorn' $pythonPath }
    throw
}
Write-Host "ATLAS LIVE DEMO session launched: http://127.0.0.1:$Port/dashboard"
Write-Host 'Check the Live Demo panel for RUNNING. Real-money trading remains disabled.'
