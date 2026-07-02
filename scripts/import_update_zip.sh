#!/usr/bin/env bash
set -euo pipefail
SRC="${1:-}"
if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  echo "Usage: ./scripts/import_update_zip.sh /path/to/update.zip" >&2
  exit 2
fi
mkdir -p updates
cp "$SRC" "updates/$(basename "$SRC")"
echo "Imported: updates/$(basename "$SRC")"
