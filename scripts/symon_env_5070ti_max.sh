#!/usr/bin/env bash
# Source this from any SyMoNeuRaL launcher before starting llama.cpp/sd.cpp.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ROOT/config/rtx5070ti_14_15gb.env"
set +a
