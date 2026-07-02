#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p bin

link_first() {
  local name="$1"; shift
  local target=""
  for p in "$@"; do
    if [ -e "$p" ]; then target="$p"; break; fi
  done
  if [ -n "$target" ]; then
    ln -sf "../$target" "bin/$name"
    echo "linked bin/$name -> $target"
  else
    echo "warning: could not find binary for $name" >&2
  fi
}

link_first symon-llama-server \
  engines/llama.cpp/build/bin/llama-server \
  engines/llama.cpp/build/bin/server

link_first symon-llama-cli \
  engines/llama.cpp/build/bin/llama-cli \
  engines/llama.cpp/build/bin/main

link_first symon-sd-server \
  engines/stable-diffusion.cpp/build/bin/sd-server \
  engines/stable-diffusion.cpp/build/examples/server/sd-server \
  engines/stable-diffusion.cpp/build/bin/server

if [ -f engines/llama.cpp/convert_hf_to_gguf.py ]; then
  cat > bin/symon-hf_to_gguf <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/engines/llama.cpp/convert_hf_to_gguf.py" "$@"
SH
  chmod +x bin/symon-hf_to_gguf
fi
