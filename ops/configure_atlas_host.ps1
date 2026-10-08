# Run once in Administrator PowerShell on the existing ATLAS host.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator PowerShell is required.' }
foreach ($name in @('ATLAS Private Backend','ATLAS Web Frontend')) {
    $task = Get-ScheduledTask -TaskName $name
    $settings = $task.Settings
    $settings.DisallowStartIfOnBatteries = $false
    $settings.StopIfGoingOnBatteries = $false
    $settings.StartWhenAvailable = $true
    Set-ScheduledTask -TaskName $name -Settings $settings | Out-Null
}
powercfg /change standby-timeout-ac 0
if ($LASTEXITCODE -ne 0) { throw 'Sleep timeout update failed.' }
powercfg /change hibernate-timeout-ac 0
if ($LASTEXITCODE -ne 0) { throw 'Hibernate timeout update failed.' }
Write-Output 'ATLAS task battery settings and AC idle settings updated. Explicit sleep and power-off still stop hosting.'
