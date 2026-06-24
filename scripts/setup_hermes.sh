#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .gitmodules ]]; then
  git submodule update --init --recursive hermes-agent
  echo "Hermes Agent submodule ready at $ROOT/hermes-agent"
else
  TARGET="$ROOT/hermes-agent"
  if [[ -d "$TARGET/.git" ]]; then
    git -C "$TARGET" pull --ff-only origin main
  else
    git clone --depth 1 https://github.com/nousresearch/hermes-agent.git "$TARGET"
  fi
  echo "Hermes Agent cloned at $TARGET"
fi