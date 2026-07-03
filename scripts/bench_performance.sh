#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== SyMoNeuRaL full performance benchmark =="
python test.py
python bench.py
python scripts/perf_report.py

echo
echo "Newest logs:"
ls -lt logs/*metrics* logs/*.json logs/*.log 2>/dev/null | head -20
