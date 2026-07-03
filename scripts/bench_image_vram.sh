#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="$PWD/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$PWD/.venv/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

IMAGE_W="${SYMON_BENCH_IMAGE_WIDTH:-1152}"
IMAGE_H="${SYMON_BENCH_IMAGE_HEIGHT:-1152}"
IMAGE_STEPS="${SYMON_BENCH_IMAGE_STEPS:-40}"

echo "== SyMoNeuRaL image-only VRAM benchmark =="
echo "image benchmark: ${IMAGE_W}x${IMAGE_H} steps=${IMAGE_STEPS}"

"$PYTHON_BIN" bench.py --skip-writer --skip-code --image-width "$IMAGE_W" --image-height "$IMAGE_H" --image-steps "$IMAGE_STEPS"
"$PYTHON_BIN" scripts/perf_report.py || true
