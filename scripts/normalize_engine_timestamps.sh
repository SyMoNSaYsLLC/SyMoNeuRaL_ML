#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
find engines/symon-llm.cpp engines/symon-image.cpp -exec touch {} +
echo "Engine source timestamps normalized."
