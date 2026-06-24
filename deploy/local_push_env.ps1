# Copy local .env to VPS (run from repo root after SSH key is configured)
param(
    [string]$Host = "45.32.224.147",
    [string]$User = "root",
    [string]$RemoteDir = "/opt/grok-bot-1"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path ".env")) {
    Write-Error ".env not found — copy from .env.example and fill keys"
}

scp .env "${User}@${Host}:${RemoteDir}/.env"
ssh "${User}@${Host}" "cd ${RemoteDir} && bash deploy/vps_setup.sh"
Write-Host "Deploy complete. Check webhook URL printed by vps_setup.sh"