$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\KHAT W TELEPHONE\Trading-ai-atlas-agent-v2'
$python = 'C:\Users\KHAT W TELEPHONE\Trading-ai\.venv\Scripts\python.exe'
$script = Join-Path $repo 'scripts\atlas_windows_watchdog.py'
$state = 'C:\Users\KHAT W TELEPHONE\ATLAS_Backup\server'
$arguments = '"' + $script + '" --state-dir "' + $state + '"'
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$logon = New-ScheduledTaskTrigger -AtLogOn -User $user
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'ATLAS Windows Supervisor' -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $settings -Force | Select-Object TaskName,State
Start-ScheduledTask -TaskName 'ATLAS Windows Supervisor'
