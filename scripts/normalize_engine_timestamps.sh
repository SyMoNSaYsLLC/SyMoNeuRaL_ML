#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
find engines/llama.cpp engines/stable-diffusion.cpp -exec touch {} +
echo "Engine source timestamps normalized."
