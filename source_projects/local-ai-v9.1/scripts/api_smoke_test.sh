#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
echo "== health =="
curl -s "$BASE/api/health" | python3 -m json.tool || true
echo "== catalog =="
curl -s "$BASE/api/v1/catalog" | python3 -m json.tool || true
echo "== writer smoke =="
curl -s -X POST "$BASE/api/v1/generate" -H 'Content-Type: application/json' -d '{"engine":"chat","prompt":"Write one clean sentence that says SyMoNeuRaL is online.","max_tokens":80}' | head -c 500
