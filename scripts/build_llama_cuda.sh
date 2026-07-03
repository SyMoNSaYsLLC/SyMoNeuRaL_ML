#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "clean" ]; then
  sudo rm -rf engines/symon-llm.cpp/build
fi

if [ ! -d engines/symon-llm.cpp ]; then
  echo "Missing engines/symon-llm.cpp. Copy or clone llama.cpp there." >&2
  exit 2
fi

mkdir -p engines/symon-llm.cpp/build
cmake -S engines/symon-llm.cpp -B engines/symon-llm.cpp/build \
  -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" \
  -DGGML_CUDA="${GGML_CUDA:-ON}" \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_TESTS=OFF

cmake --build engines/symon-llm.cpp/build --config "${CMAKE_BUILD_TYPE:-Release}" -j "${SYMON_BUILD_JOBS:-$(nproc)}"

echo
echo "llama.cpp CUDA build complete."
echo "Expected binaries:"
find engines/symon-llm.cpp/build -maxdepth 4 -type f \( -name 'llama-server' -o -name 'llama-cli' -o -name 'llama-quantize' \) -print

# ensure config.yaml path works
mkdir -p engines/symon-llm.cpp/build/bin
if [ ! -e bin/symon-llm-server ]; then
  found="$(find engines/symon-llm.cpp/build -type f -name 'llama-server' | head -n1 || true)"
  if [ -n "$found" ]; then
    ln -sf "$(realpath --relative-to=engines/symon-llm.cpp/build/bin "$found")" bin/symon-llm-server
    echo "linked bin/symon-llm-server -> $found"
  fi
fi
