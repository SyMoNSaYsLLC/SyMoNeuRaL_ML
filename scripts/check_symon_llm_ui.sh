#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:8080/ | grep -E 'SyMoNeuRaL LLM Engine' >/dev/null
curl -fsS http://127.0.0.1:8080/v1/models >/dev/null
echo "SyMoNeuRaL LLM engine UI is branded and API is reachable."
