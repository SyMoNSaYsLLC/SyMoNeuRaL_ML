#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-$HOME/local-ai}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TARGET/services" "$TARGET/ui/css" "$TARGET/ui/js" "$TARGET/docs" "$TARGET/helpers" "$TARGET/scripts"
backup_if_exists(){ local path="$1"; [ -e "$path" ] && cp -a "$path" "${path}.bak-${STAMP}"; }
for file in main.py requirements.txt; do backup_if_exists "$TARGET/$file"; cp "$SRC_DIR/$file" "$TARGET/$file"; done
for file in gemma.py writer.py diff.py; do backup_if_exists "$TARGET/services/$file"; cp "$SRC_DIR/services/$file" "$TARGET/services/$file"; done
for file in index.html; do backup_if_exists "$TARGET/ui/$file"; cp "$SRC_DIR/ui/$file" "$TARGET/ui/$file"; done
for file in style.css; do backup_if_exists "$TARGET/ui/css/$file"; cp "$SRC_DIR/ui/css/$file" "$TARGET/ui/css/$file"; done
for file in app.js; do backup_if_exists "$TARGET/ui/js/$file"; cp "$SRC_DIR/ui/js/$file" "$TARGET/ui/js/$file"; done
cp -a "$SRC_DIR/docs/." "$TARGET/docs/"
cp -a "$SRC_DIR/helpers/." "$TARGET/helpers/"
cp -a "$SRC_DIR/scripts/." "$TARGET/scripts/"
chmod +x "$TARGET/scripts/"*.sh 2>/dev/null || true
chmod +x "$TARGET/main.py"
cat <<MSG
Installed SyMoNeuRaL v9.1 into: $TARGET
Run:
  cd $TARGET
  source .venv/bin/activate
  pip install -r requirements.txt
  SYMON_CHAT_GPU_LAYERS=16 SYMON_CHAT_CTX=2048 python main.py
Browser:
  http://127.0.0.1:8000
API docs:
  http://127.0.0.1:8000/docs
MSG
