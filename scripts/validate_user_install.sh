#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "SyMoNeuRaL_ML user install validation"
echo "====================================="
cat VERSION

echo "[1/5] Required docs"
test -f README.md
test -f docs/USER_INSTALL_GUIDE.md
test -f docs/GPU_SERVER_BUILD_MATRIX.md
test -f docs/CUDA_MODEL_TOOLS.md

echo "[2/5] Python compile check"
python3 -m compileall app symon_tools >/dev/null

echo "[3/5] Tool scripts"
test -x scripts/install.sh
test -x scripts/build_all_cuda.sh
test -x scripts/install_path_tools.sh
test -x scripts/start_exclusive_16gb.sh

echo "[4/5] NVIDIA visibility"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true
else
  echo "nvidia-smi not found; install/check NVIDIA driver before CUDA inference."
fi

echo "[5/5] Model placeholders"
find models -maxdepth 3 -type f 2>/dev/null || true

echo "Validation complete."
