param(
  [string]$Cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe',
  [string]$TokenFile = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cloudflared\ATLAS-Window.token')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Cloudflared -PathType Leaf)) {
  throw 'Cloudflare connector is not installed at the configured path.'
}
if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) {
  throw 'The existing ATLAS tunnel credential file is unavailable.'
}
# Reuse the existing remotely managed tunnel. Never print or copy its token.
& $Cloudflared tunnel --protocol http2 run --token-file $TokenFile
exit $LASTEXITCODE
