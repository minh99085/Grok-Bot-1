#!/usr/bin/env bash
# Hermes Agent is vendored in hermes-agent/ — run install from that directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES="$ROOT/hermes-agent"
if [[ ! -d "$HERMES" ]]; then
  echo "hermes-agent/ not found — pull latest from Grok-Bot-1 main"
  exit 1
fi
echo "Hermes Agent source at $HERMES ($(find "$HERMES" -maxdepth 0 -type d))"
echo "Install: cd hermes-agent && see README or https://hermes-agent.nousresearch.com"