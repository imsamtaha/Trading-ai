param(
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [string]$PythonPath = "python"
)
$ErrorActionPreference = "Stop"
try {
    $root = (Resolve-Path -LiteralPath $ProjectPath).Path
    $runner = Join-Path $root "run_atlas_mt5.py"
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
        throw "run_atlas_mt5.py is missing from ProjectPath."
    }
    # Values are inherited by the child; dotenv does not override them.
    $env:ATLAS_LIVE_TRADING = "false"
    $env:MT5_READONLY_MODE = "true"
    $env:MT5_REQUIRE_DEMO = "true"
    Push-Location -LiteralPath $root
    try {
        & $PythonPath -u $runner
        $workerExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    exit $workerExitCode
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
