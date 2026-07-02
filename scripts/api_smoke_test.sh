#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
curl -s "$BASE/api/v1/catalog" | python3 -m json.tool
curl -s "$BASE/api/v1/tools/vram" | python3 -m json.tool
curl -s -X POST "$BASE/api/v1/fine-tune/plan" -H 'Content-Type: application/json' -d '{"examples":[{"prompt":"hi","completion":"hello"}]}' | python3 -m json.tool
