#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
APP_ROOT="clients/iptv/symoneural-view/usr/lib/symoneural-view"
APP="$APP_ROOT/symoneural-view.py"

if [ ! -f "$APP" ]; then
  echo "Missing SyMoNeuRaL-View app: $APP" >&2
  exit 1
fi

export PYTHONPATH="$PWD/$APP_ROOT:${PYTHONPATH:-}"
export SYMON_IPTV_INDEX_DIR="${SYMON_IPTV_INDEX_DIR:-$PWD/data/iptv/index}"

if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland}"
else
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

exec python3 "$APP" "$@"
