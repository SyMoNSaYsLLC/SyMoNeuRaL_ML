#!/usr/bin/env bash
set -euo pipefail
curl -s http://127.0.0.1:8000/api/v1/coder/jobs | python3 -m json.tool
