#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="$PWD/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$PWD/.venv/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

echo "== SyMoNeuRaL full performance benchmark =="
echo "python: $PYTHON_BIN"

"$PYTHON_BIN" test.py
"$PYTHON_BIN" bench.py --image-width "${SYMON_BENCH_IMAGE_WIDTH:-768}" --image-height "${SYMON_BENCH_IMAGE_HEIGHT:-768}" --image-steps "${SYMON_BENCH_IMAGE_STEPS:-32}"
"$PYTHON_BIN" scripts/perf_report.py || true

echo
echo "Newest logs:"
ls -lt logs/*metrics* logs/*.json logs/*.log 2>/dev/null | head -20
