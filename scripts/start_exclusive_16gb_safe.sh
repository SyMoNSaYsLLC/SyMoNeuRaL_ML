#!/usr/bin/env bash

# SyMoNeuRaL permanent RTX 5070 Ti 14-15GB VRAM profile.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT/scripts/symon_env_5070ti_max.sh" ]; then
  source "$ROOT/scripts/symon_env_5070ti_max.sh"
fi
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

# Writer/manager stays resident and light. Code/Image get exclusive GPU during handoff.
export SYMON_CHAT_GPU_LAYERS="${SYMON_CHAT_GPU_LAYERS:-16}"
export SYMON_CHAT_CTX="${SYMON_CHAT_CTX:-2048}"
export SYMON_CODE_GPU_LAYERS="${SYMON_CODE_GPU_LAYERS:-999}"
export SYMON_DEFAULT_BATCH="${SYMON_DEFAULT_BATCH:-512}"
export SYMON_DEFAULT_UBATCH="${SYMON_DEFAULT_UBATCH:-128}"
export SYMON_HANDOFF_MAX_ROUNDS="${SYMON_HANDOFF_MAX_ROUNDS:-2}"

python main.py
