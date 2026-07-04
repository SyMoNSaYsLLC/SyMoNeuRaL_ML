#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
SRC="${1:-./IPTV_Playlist.zip}"

if [ ! -e "$SRC" ]; then
  echo "Missing playlist source: $SRC" >&2
  echo "Usage: ./scripts/import_iptv_playlist_zip.sh /path/to/IPTV_Playlist.zip" >&2
  echo "       ./scripts/import_iptv_playlist_zip.sh /path/to/IPTV_Playlist" >&2
  exit 1
fi

mkdir -p data/iptv/index
python3 scripts/build_iptv_index.py "$SRC" --out data/iptv/index

echo
printf 'IPTV index ready: %s\n' "$PWD/data/iptv/index/summary.json"
printf 'API status after ./scripts/symon: http://127.0.0.1:8000/api/iptv/status\n'
