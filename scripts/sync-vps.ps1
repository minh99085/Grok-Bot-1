# Sync GitHub main -> Bot 1 VPS (45.32.227.242). Never targets Bot 2.
param(
    [switch]$SkipRebuild,
    [switch]$Rebuild,
    [switch]$VerifyOnly,
    [string]$SshKey = "$env:USERPROFILE\.ssh\bot1_grok_temp",
    [string]$VpsHost = "45.32.227.242",
    [string]$VpsUser = "linuxuser",
    [string]$VpsRepo = "/opt/Grok-Bot-1",
    [string]$PluginPath = "/opt/Grok-Bot-1/hermes-agent-main/plugins/hermes-trading-engine"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-Error "Not a git repo: $RepoRoot"
}
if ($RepoRoot -notmatch "Grok-Bot-1") {
    Write-Error "SAFETY: sync-vps.ps1 in Grok-Bot-1 only. Bot2 uses Grok-Bot-1 repo."
}
Set-Location $RepoRoot

function Get-ShortSha([string]$sha) { if ($sha.Length -ge 7) { $sha.Substring(0, 7) } else { $sha } }

$doRebuild = -not $SkipRebuild
Write-Host "BOT1 deploy -> $VpsUser@${VpsHost}:$VpsRepo"

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& git fetch origin main 2>&1 | Out-Null
$ErrorActionPreference = $prevEap
$local = (git rev-parse HEAD).Trim()
$origin = (git rev-parse origin/main 2>$null).Trim()
if (-not $origin) { $origin = $local }

if ($local -ne $origin) {
    Write-Error "Local HEAD ($local) != origin/main ($origin). Push or pull first."
}

$sshArgs = @("-i", $SshKey, "-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=no", "${VpsUser}@${VpsHost}")
$vpsHead = (ssh @sshArgs "git -C $VpsRepo rev-parse HEAD 2>/dev/null || echo MISSING").Trim()

Write-Host "origin/main : $(Get-ShortSha $origin) $origin"
Write-Host "VPS HEAD    : $(Get-ShortSha $vpsHead) $vpsHead"

if ($vpsHead -eq $origin) {
    Write-Host "SYNC OK - VPS already matches origin/main."
    if ($VerifyOnly) { exit 0 }
    if (-not $doRebuild) { exit 0 }
} elseif ($VerifyOnly) {
    Write-Error "SYNC FAIL - VPS diverged from origin/main."
}

if ($vpsHead -eq "MISSING" -or $vpsHead.Length -lt 40) {
    Write-Host "First deploy: cloning repo on VPS..."
    $bootstrap = @"
set -e
sudo mkdir -p $VpsRepo
sudo chown -R ${VpsUser}:${VpsUser} $VpsRepo
if [ ! -d $VpsRepo/.git ]; then
  git clone https://github.com/minh99085/Grok-Bot-1.git $VpsRepo
fi
cd $VpsRepo
git fetch origin main
git reset --hard origin/main
git clean -fd
echo VPS_HEAD=`$(git rev-parse HEAD)
"@
    ssh @sshArgs $bootstrap
    $vpsHead = (ssh @sshArgs "git -C $VpsRepo rev-parse HEAD").Trim()
}

$bundle = Join-Path $env:TEMP "grok-bot1-sync.bundle"
if ($vpsHead -ne $origin) {
    Write-Host "Creating bundle $vpsHead..$origin ..."
    & git bundle create $bundle "HEAD" "^$vpsHead"
    if (-not (Test-Path $bundle)) {
        Write-Error "Bundle creation failed. VPS=$vpsHead origin=$origin"
    }
    scp -i $SshKey -o StrictHostKeyChecking=no $bundle "${VpsUser}@${VpsHost}:/tmp/grok-bot1-sync.bundle"
    $remote = @"
set -e
cd $VpsRepo
git fetch /tmp/grok-bot1-sync.bundle HEAD:refs/remotes/bundle/main
git reset --hard bundle/main
git clean -fd
rm -f /tmp/grok-bot1-sync.bundle
echo VPS_HEAD=`$(git rev-parse HEAD)
"@
    ssh @sshArgs $remote
    Remove-Item -Force $bundle -ErrorAction SilentlyContinue
}

if ($doRebuild) {
    $docker = @"
set -e
cd $VpsRepo
python3 scripts/apply-loop-arch-env.py
python3 scripts/pulse-babysit/validate-frozen-lock.py || exit 1
cd $PluginPath
docker compose down --remove-orphans
docker compose build
docker compose up -d --force-recreate --remove-orphans
sleep 8
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'hermes-training|hermes-trading-engine'
"@
    ssh @sshArgs $docker
}

$vpsAfter = (ssh @sshArgs "git -C $VpsRepo rev-parse HEAD").Trim()
if ($vpsAfter -ne $origin) {
    Write-Error "SYNC FAIL after deploy: VPS=$vpsAfter origin=$origin"
}

Write-Host "BOT1 SYNC OK - VPS HEAD matches origin/main ($(Get-ShortSha $origin))."
exit 0