#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_SKILLS="${HERMES_HOME:-$HOME/.hermes}/skills"
mkdir -p "$HERMES_SKILLS"
ln -sfn "$ROOT/skills/grok-bot-profit-discovery" "$HERMES_SKILLS/grok-bot-profit-discovery"
echo "Linked skill to $HERMES_SKILLS/grok-bot-profit-discovery"