#!/usr/bin/env bash
set -euo pipefail

if [ ! -f pyproject.toml ] || [ ! -d scripts ]; then
  echo "Run from the SyMoNeuRaL_ML repository root." >&2
  exit 1
fi

mapfile -t ZIPS < <(
  {
    find . -maxdepth 1 -type f \( -name "*update*.zip" -o -name "*hotfix*.zip" \) 2>/dev/null || true
    find updates -maxdepth 1 -type f -name "*.zip" 2>/dev/null || true
    find update_zips -maxdepth 1 -type f -name "*.zip" 2>/dev/null || true
  } | sort -u
)

if [ "${#ZIPS[@]}" -eq 0 ]; then
  echo "No update zips found."
  exit 0
fi

for z in "${ZIPS[@]}"; do
  echo
  echo "== Applying $z =="
  ./scripts/apply_update_zip.sh "$z"
done
