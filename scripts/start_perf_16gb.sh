#!/usr/bin/env bash

# SyMoNeuRaL permanent RTX 5070 Ti 14-15GB VRAM profile.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT/scripts/symon_env_5070ti_max.sh" ]; then
  source "$ROOT/scripts/symon_env_5070ti_max.sh"
fi
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./scripts/start_exclusive_16gb.sh
