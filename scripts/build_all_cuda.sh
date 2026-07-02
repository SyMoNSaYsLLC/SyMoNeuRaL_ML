#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/build_llama_cuda.sh "${1:-}"
./scripts/build_stable_diffusion_cuda.sh "${1:-}"
./scripts/symon_link_binaries.sh
