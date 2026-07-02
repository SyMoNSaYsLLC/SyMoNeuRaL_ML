#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-../SyMoNeuRaL_Local_ML_shipping_ready.zip}"
./scripts/production_check.sh
rm -f "$OUT"
find . -name '__pycache__' -type d -prune -exec rm -rf {} +
zip -r "$OUT" . -x '*.pyc' 'logs/*' '.venv/*' '.git/*'
echo "Wrote $OUT"
