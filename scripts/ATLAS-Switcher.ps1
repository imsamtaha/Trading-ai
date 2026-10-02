param([ValidateSet('GUI','Start','Status')][string]$Action='GUI')
$ErrorActionPreference='Stop'
function Test-AtlasBackend {
  try {
    $r=Invoke-RestMethod 'http://127.0.0.1:8012/health' -TimeoutSec 3
    return ($r.status -eq 'healthy' -and $r.service -eq 'atlas-trading-api')
  } catch { return $false }
}
function Test-AtlasFrontend {
  try {
    $r=Invoke-WebRequest 'http://127.0.0.1:8011/admin/runtime' -UseBasicParsing -TimeoutSec 3
    return ($r.StatusCode -eq 200 -and $r.Content -match 'ATLAS Runtime')
  } catch { return $false }
}
function Get-AtlasStatus {
  [pscustomobject]@{ Backend=(Test-AtlasBackend); Frontend=(Test-AtlasFrontend) }
}
function Start-AtlasTask([string]$Name,[int]$Port) {
  $task=Get-ScheduledTask -TaskName $Name -ErrorAction Stop
  if ($task.State -eq 'Running') { return }
  if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is occupied by an unhealthy or older service. No duplicate process was started."
  }
  Start-ScheduledTask -TaskName $Name
}
function Wait-AtlasService([scriptblock]$Check,[string]$Name) {
  $deadline=[DateTime]::UtcNow.AddSeconds(60)
  do {
    if (& $Check) { return }
    Start-Sleep -Milliseconds 750
  } while ([DateTime]::UtcNow -lt $deadline)
  throw "$Name did not become healthy within 60 seconds. Inspect its launcher."
}
function Start-Atlas {
  if (-not (Test-AtlasBackend)) {
    Start-AtlasTask 'ATLAS Private Backend' 8012
    Wait-AtlasService { Test-AtlasBackend } 'Backend'
  }
  if (-not (Test-AtlasFrontend)) {
    Start-AtlasTask 'ATLAS Web Frontend' 8011
    Wait-AtlasService { Test-AtlasFrontend } 'Frontend'
  }
  Get-AtlasStatus
}
if ($Action -eq 'Status') { Get-AtlasStatus | ConvertTo-Json; exit }
if ($Action -eq 'Start') { Start-Atlas | ConvertTo-Json; exit }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form=New-Object System.Windows.Forms.Form
$form.Text='ATLAS Runtime Switcher'
$form.Size=New-Object System.Drawing.Size(480,260)
$form.StartPosition='CenterScreen'
$label=New-Object System.Windows.Forms.Label
$label.SetBounds(20,20,420,70)
$label.Text='Start ATLAS services, then use the owner panel for demo orders.'
$start=New-Object System.Windows.Forms.Button
$start.SetBounds(20,100,200,45)
$start.Text='START ATLAS'
$open=New-Object System.Windows.Forms.Button
$open.SetBounds(240,100,200,45)
$open.Text='OPEN OWNER SWITCHER'
$refresh=New-Object System.Windows.Forms.Button
$refresh.SetBounds(20,160,420,35)
$refresh.Text='REFRESH STATUS'
$refresh.Add_Click({
  $s=Get-AtlasStatus
  $label.Text="Backend: $($s.Backend) | Owner panel: $($s.Frontend)"
})
$start.Add_Click({
  $start.Enabled=$false; $open.Enabled=$false; $refresh.Enabled=$false
  $label.Text='Starting services and verifying health...'
  $form.Refresh()
  try {
    $s=Start-Atlas
    $label.Text="Backend: $($s.Backend) | Owner panel: $($s.Frontend)"
  } catch { $label.Text=$_.Exception.Message }
  finally { $start.Enabled=$true; $open.Enabled=$true; $refresh.Enabled=$true }
})
$open.Add_Click({ Start-Process 'https://justai-atlas.online/admin/runtime' })
$form.Controls.AddRange(@($label,$start,$open,$refresh))
[void]$form.ShowDialog()
