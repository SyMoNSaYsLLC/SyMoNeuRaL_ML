#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "This launcher is legacy. Using canonical ./scripts/symon"
exec "$ROOT/scripts/symon" "$@"
