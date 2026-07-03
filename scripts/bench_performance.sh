#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="$PWD/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$PWD/.venv/bin/python3"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

echo "== SyMoNeuRaL full performance benchmark =="
echo "python: $PYTHON_BIN"

"$PYTHON_BIN" test.py
"$PYTHON_BIN" bench.py
"$PYTHON_BIN" scripts/perf_report.py

echo
echo "Newest logs:"
ls -lt logs/*metrics* logs/*.json logs/*.log 2>/dev/null | head -20
