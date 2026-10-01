$ErrorActionPreference = 'Stop'
$stage = Join-Path $env:USERPROFILE 'ATLAS_Backup\vps-staging\20261001-prepared'
New-Item -ItemType Directory -Path $stage -Force | Out-Null
$repos = [ordered]@{
  frontend = 'C:\Users\KHAT W TELEPHONE\Trading-ai\.worktrees\atlas-clean-followup'
  backend = 'C:\Users\KHAT W TELEPHONE\Trading-ai\.worktrees\atlas-private-multiuser'
  council = 'C:\Users\KHAT W TELEPHONE\Trading-ai-atlas-agent-v2'
}
$manifest = [ordered]@{
  status = 'PREPARED_NOT_ACTIVATED'
  created_utc = (Get-Date).ToUniversalTime().ToString('o')
  server_provisioned = $false
  tasks_registered = $false
  secrets_included = $false
  trading_enabled_on_target = $false
  sources = @{}
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($name in $repos.Keys) {
  $source = $repos[$name]
  $head = (& git -C $source rev-parse HEAD).Trim()
  if ($LASTEXITCODE -ne 0) { throw "Cannot resolve $name" }
  $archive = Join-Path $stage "$name-source.zip"
  & git -C $source archive --format=zip "--output=$archive" HEAD
  if ($LASTEXITCODE -ne 0) { throw "Archive failed: $name" }
  $zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
  try {
    if ($zip.Entries.Count -eq 0) { throw 'Empty archive' }
    foreach ($entry in $zip.Entries) {
      $base = [System.IO.Path]::GetFileName($entry.FullName)
      if ($base -eq '.env' -or $base -match '\.env$|\.token$|^credentials\.json$|^OPEN AI API\.txt$') {
        throw "Private configuration detected in $name archive; package blocked"
      }
    }
    $count = $zip.Entries.Count
  } finally { $zip.Dispose() }
  $manifest.sources[$name] = @{commit=$head; archive="$name-source.zip"; entries=$count; sha256=(Get-FileHash $archive -Algorithm SHA256).Hash}
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $stage 'manifest.json') -Encoding UTF8
Copy-Item (Join-Path $repos.council 'docs\windows-vps-prepared.md') (Join-Path $stage 'README.md') -Force
Write-Output "PACKAGE_STATUS=$($manifest.status)"
Write-Output "PACKAGE_PATH=$stage"
foreach ($name in $manifest.sources.Keys) { Write-Output "$name VERIFIED entries=$($manifest.sources[$name].entries) commit=$($manifest.sources[$name].commit)" }

