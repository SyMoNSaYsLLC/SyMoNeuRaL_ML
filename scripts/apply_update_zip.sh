#!/usr/bin/env bash
set -euo pipefail

ZIP="${1:-}"
if [ ! -f pyproject.toml ] || [ ! -d scripts ]; then
  echo "Run from the SyMoNeuRaL_ML repository root." >&2
  exit 1
fi
if [ -z "$ZIP" ]; then
  echo "Usage: ./scripts/apply_update_zip.sh ./update.zip" >&2
  exit 2
fi
if [ ! -f "$ZIP" ]; then
  echo "Update zip not found: $ZIP" >&2
  exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Extracting update: $ZIP"
unzip -q "$ZIP" -d "$TMP"

APPLY="$(find "$TMP" -type f \( -name "UPDATE.sh" -o -name "apply_main_hotfix.sh" -o -name "apply_update.sh" -o -name "apply_repo_update.sh" -o -name "apply_hotfix.sh" -o -name "apply_update_runner_hotfix.sh" \) | sort | head -n 1)"

if [ -z "$APPLY" ]; then
  echo "No known update script found inside $ZIP." >&2
  echo "Expected: UPDATE.sh, apply_main_hotfix.sh, apply_update.sh, apply_repo_update.sh, apply_hotfix.sh, or apply_update_runner_hotfix.sh" >&2
  exit 3
fi

chmod +x "$APPLY"
echo "Running: $APPLY"
"$APPLY"
