#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 engines/llama.cpp/convert_hf_to_gguf.py "$@"
