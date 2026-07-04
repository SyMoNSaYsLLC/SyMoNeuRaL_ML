#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PATCH_SOURCE="${PATCH_SOURCE:-}"

if [ -z "$PATCH_SOURCE" ]; then
  echo "ERROR: PATCH_SOURCE is not set. Use the update zip via apply_update_zip.sh." >&2
  exit 1
fi

FILES_DIR="$PATCH_SOURCE/files"
[ -d "$FILES_DIR" ] || { echo "ERROR: missing files directory: $FILES_DIR" >&2; exit 1; }

echo "== Migrate MATLAB tools into SyMoNeuRaL =="

mkdir -p matlab/vendor matlab/+symon docs

sudo rm -rf matlab/vendor/mathworks-llms-with-matlab
sudo rm -rf matlab/vendor/mathworks-image-classifier-app

cp -a "$FILES_DIR/matlab/vendor/mathworks-llms-with-matlab" matlab/vendor/
cp -a "$FILES_DIR/matlab/vendor/mathworks-image-classifier-app" matlab/vendor/
cp -a "$FILES_DIR/matlab/+symon" matlab/
cp -f "$FILES_DIR/matlab/README.md" matlab/README.md
cp -f "$FILES_DIR/docs/MATLAB_TOOL_MIGRATION.md" docs/MATLAB_TOOL_MIGRATION.md

# Do not allow nested repo metadata.
sudo rm -rf matlab/vendor/mathworks-llms-with-matlab/.git
sudo rm -rf matlab/vendor/mathworks-image-classifier-app/.git

# Keep external MATLAB tool sources transparent for GitHub Linguist while still
# letting project-owned wrappers count as MATLAB.
if [ ! -f .gitattributes ]; then
  touch .gitattributes
fi

grep -q 'matlab/vendor/mathworks-llms-with-matlab' .gitattributes || cat >> .gitattributes <<'EOF'

# External MATLAB tools migrated for SyMoNeuRaL MATLAB layer.
# Project-owned wrappers under matlab/+symon still count as MATLAB.
matlab/vendor/mathworks-llms-with-matlab/** linguist-vendored
matlab/vendor/mathworks-image-classifier-app/** linguist-vendored
EOF

git add \
  .gitattributes \
  matlab/README.md \
  matlab/+symon \
  matlab/vendor/mathworks-llms-with-matlab \
  matlab/vendor/mathworks-image-classifier-app \
  docs/MATLAB_TOOL_MIGRATION.md \
  scripts/migrate_matlab_tools.sh

if git diff --cached --quiet; then
  echo "No staged MATLAB migration changes."
else
  git commit -m "vendor: migrate MATLAB LLM and image classifier tools"
  git push origin main
fi

echo
echo "Done."
echo "MATLAB entrypoint:"
echo "  symon.addPaths"
echo "Docs:"
echo "  docs/MATLAB_TOOL_MIGRATION.md"
