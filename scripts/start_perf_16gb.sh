#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./scripts/start_exclusive_16gb.sh
