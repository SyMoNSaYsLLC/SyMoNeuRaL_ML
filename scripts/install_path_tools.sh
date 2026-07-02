#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p "$HOME/.local/bin"
python3 -m pip install -e . >/dev/null

for cmd in symon-server symon-web symon-cli symon-build symon-hf_to_gguf symon-vram; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd -> $(command -v "$cmd")"
  else
    echo "warning: $cmd was not found after pip editable install" >&2
  fi
done

./scripts/symon_link_binaries.sh || true

for f in bin/symon-*; do
  [ -e "$f" ] || continue
  ln -sf "$(pwd)/$f" "$HOME/.local/bin/$(basename "$f")"
done

cat <<'MSG'

Add this to ~/.bashrc or ~/.zshrc if needed:

  export PATH="$HOME/.local/bin:$PATH"

Then reload:

  source ~/.bashrc

Main commands:
  symon-server
  symon-web
  symon-cli health
  symon-cli vram
  symon-build all
  symon-build llama
  symon-build sd
  symon-hf_to_gguf /path/to/hf-model --outfile models/llm/model.gguf
  symon-vram

Engine binary symlinks, after build:
  symon-llama-server
  symon-llama-cli
  symon-sd-server
MSG
