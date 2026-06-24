#!/usr/bin/env bash
# Register Grok-Bot-1 cron jobs with Hermes (requires `hermes` CLI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GROK_BOT_ROOT="$ROOT"
if ! command -v hermes >/dev/null 2>&1; then
  echo "hermes CLI not found — install Hermes Agent first (scripts/setup_hermes.sh)"
  exit 1
fi
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
root = Path(os.environ["GROK_BOT_ROOT"])
jobs = json.loads((root / "hermes_integration/cron_jobs.json").read_text())
for job in jobs:
    cmd = job["command"].replace("${GROK_BOT_ROOT}", str(root))
    subprocess.run(
        ["hermes", "cron", "add", "--name", job["name"], "--schedule", job["schedule"], "--command", cmd],
        check=False,
    )
    print(f"registered: {job['name']}")
PY