#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== SyMoNeuRaL 14GB VRAM target benchmark =="
echo "Default image pass: 1024x1024 / 36 steps"
./scripts/bench_performance.sh

echo
echo "If max GPU memory is still below 14000 MiB, run the heavier image-only pass:"
echo "  SYMON_BENCH_IMAGE_WIDTH=1152 SYMON_BENCH_IMAGE_HEIGHT=1152 SYMON_BENCH_IMAGE_STEPS=40 python bench.py --skip-writer --skip-code"
