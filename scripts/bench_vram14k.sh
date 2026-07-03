#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== SyMoNeuRaL 14GB+ VRAM target benchmark =="
echo "Default image pass: 1152x1152 / 40 steps"
./scripts/bench_performance.sh

echo
echo "If max GPU memory is still below 14000 MiB, run:"
echo "  SYMON_BENCH_IMAGE_WIDTH=1216 SYMON_BENCH_IMAGE_HEIGHT=1216 SYMON_BENCH_IMAGE_STEPS=40 ./scripts/bench_performance.sh"
echo
echo "If it OOMs, fallback:"
echo "  SYMON_BENCH_IMAGE_WIDTH=1024 SYMON_BENCH_IMAGE_HEIGHT=1024 SYMON_BENCH_IMAGE_STEPS=36 ./scripts/bench_performance.sh"
