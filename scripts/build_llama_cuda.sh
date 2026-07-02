#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "clean" ]; then
  sudo rm -rf engines/llama.cpp/build
fi

if [ ! -d engines/llama.cpp ]; then
  echo "Missing engines/llama.cpp. Copy or clone llama.cpp there." >&2
  exit 2
fi

mkdir -p engines/llama.cpp/build
cmake -S engines/llama.cpp -B engines/llama.cpp/build \
  -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" \
  -DGGML_CUDA="${GGML_CUDA:-ON}" \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_TESTS=OFF

cmake --build engines/llama.cpp/build --config "${CMAKE_BUILD_TYPE:-Release}" -j "${SYMON_BUILD_JOBS:-$(nproc)}"

echo
echo "llama.cpp CUDA build complete."
echo "Expected binaries:"
find engines/llama.cpp/build -maxdepth 4 -type f \( -name 'llama-server' -o -name 'llama-cli' -o -name 'llama-quantize' \) -print

# ensure config.yaml path works
mkdir -p engines/llama.cpp/build/bin
if [ ! -e engines/llama.cpp/build/bin/llama-server ]; then
  found="$(find engines/llama.cpp/build -type f -name 'llama-server' | head -n1 || true)"
  if [ -n "$found" ]; then
    ln -sf "$(realpath --relative-to=engines/llama.cpp/build/bin "$found")" engines/llama.cpp/build/bin/llama-server
    echo "linked engines/llama.cpp/build/bin/llama-server -> $found"
  fi
fi
