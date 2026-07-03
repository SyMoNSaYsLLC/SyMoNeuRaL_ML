#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# SyMoNeuRaL RTX 5070 Ti / 16GB exclusive-VRAM performance profile.
#
# Only one heavy worker should own the GPU at a time:
#   writer -> code -> image -> writer
#
# This profile pushes the active model harder than the conservative defaults.

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export SYMON_EXCLUSIVE_VRAM="${SYMON_EXCLUSIVE_VRAM:-true}"
export SYMON_RESIDENT_ENGINE="${SYMON_RESIDENT_ENGINE:-writer}"

# Writer / manager: Gemma 12B Q4_K_M.
# Prior logs showed only ~3.2GB process VRAM at 16 layers, so use all possible layers.
export SYMON_CHAT_GPU_LAYERS="${SYMON_CHAT_GPU_LAYERS:-999}"
export SYMON_CHAT_CTX="${SYMON_CHAT_CTX:-4096}"
export SYMON_CHAT_BATCH="${SYMON_CHAT_BATCH:-1024}"
export SYMON_CHAT_UBATCH="${SYMON_CHAT_UBATCH:-256}"
export SYMON_CHAT_PARALLEL="${SYMON_CHAT_PARALLEL:-1}"

# Coding worker: Qwen 1.5B can afford a larger context in exclusive mode.
export SYMON_CODE_GPU_LAYERS="${SYMON_CODE_GPU_LAYERS:-999}"
export SYMON_CODE_CTX="${SYMON_CODE_CTX:-8192}"
export SYMON_CODE_BATCH="${SYMON_CODE_BATCH:-1024}"
export SYMON_CODE_UBATCH="${SYMON_CODE_UBATCH:-256}"
export SYMON_CODE_PARALLEL="${SYMON_CODE_PARALLEL:-1}"

# Image worker defaults. SD 1.5 fits easily; keep 512 as compatibility default,
# but increase quality steps. Override width/height from API if needed.
export SYMON_IMAGE_WIDTH="${SYMON_IMAGE_WIDTH:-512}"
export SYMON_IMAGE_HEIGHT="${SYMON_IMAGE_HEIGHT:-512}"
export SYMON_IMAGE_STEPS="${SYMON_IMAGE_STEPS:-28}"
export SYMON_IMAGE_CFG_SCALE="${SYMON_IMAGE_CFG_SCALE:-7.5}"

# Engine readiness.
export SYMON_ENGINE_READY_TIMEOUT="${SYMON_ENGINE_READY_TIMEOUT:-300}"
export SYMON_ENGINE_READY_POLL="${SYMON_ENGINE_READY_POLL:-0.5}"

echo "== SyMoNeuRaL RTX 5070 Ti max profile =="
echo "writer gpu_layers=$SYMON_CHAT_GPU_LAYERS ctx=$SYMON_CHAT_CTX batch=$SYMON_CHAT_BATCH ubatch=$SYMON_CHAT_UBATCH"
echo "code   gpu_layers=$SYMON_CODE_GPU_LAYERS ctx=$SYMON_CODE_CTX batch=$SYMON_CODE_BATCH ubatch=$SYMON_CODE_UBATCH"
echo "image  ${SYMON_IMAGE_WIDTH}x${SYMON_IMAGE_HEIGHT} steps=$SYMON_IMAGE_STEPS"

exec python main.py
