#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="$PWD/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$PWD/.venv/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

IMAGE_W="${SYMON_BENCH_IMAGE_WIDTH:-1024}"
IMAGE_H="${SYMON_BENCH_IMAGE_HEIGHT:-1024}"
IMAGE_STEPS="${SYMON_BENCH_IMAGE_STEPS:-36}"

echo "== SyMoNeuRaL full performance benchmark =="
echo "python: $PYTHON_BIN"
echo "image benchmark: ${IMAGE_W}x${IMAGE_H} steps=${IMAGE_STEPS}"

"$PYTHON_BIN" test.py
"$PYTHON_BIN" bench.py --image-width "$IMAGE_W" --image-height "$IMAGE_H" --image-steps "$IMAGE_STEPS"
"$PYTHON_BIN" scripts/perf_report.py || true

echo
echo "Newest logs:"
ls -lt logs/*metrics* logs/*.json logs/*.log 2>/dev/null | head -20
