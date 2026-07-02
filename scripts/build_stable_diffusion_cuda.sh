#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "clean" ]; then
  sudo rm -rf engines/stable-diffusion.cpp/build
fi

if [ ! -d engines/stable-diffusion.cpp ]; then
  echo "Missing engines/stable-diffusion.cpp. Copy or clone stable-diffusion.cpp there." >&2
  exit 2
fi

mkdir -p engines/stable-diffusion.cpp/build
cmake -S engines/stable-diffusion.cpp -B engines/stable-diffusion.cpp/build \
  -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" \
  -DSD_CUDA="${SD_CUDA:-ON}" \
  -DGGML_CUDA="${GGML_CUDA:-ON}" \
  -DSD_BUILD_SERVER=ON \
  -DSD_BUILD_EXAMPLES=ON \
  -DSD_BUILD_TESTS=OFF

cmake --build engines/stable-diffusion.cpp/build --config "${CMAKE_BUILD_TYPE:-Release}" -j "${SYMON_BUILD_JOBS:-$(nproc)}"

echo
echo "stable-diffusion.cpp CUDA build complete."
echo "Expected binaries:"
find engines/stable-diffusion.cpp/build -maxdepth 5 -type f \( -name 'sd-server' -o -name 'sd' -o -name 'stable-diffusion' \) -print

# ensure config.yaml path works even if upstream puts sd-server under examples/server
mkdir -p engines/stable-diffusion.cpp/build/bin
if [ ! -e engines/stable-diffusion.cpp/build/bin/sd-server ]; then
  found="$(find engines/stable-diffusion.cpp/build -type f -name 'sd-server' | head -n1 || true)"
  if [ -n "$found" ]; then
    ln -sf "$(realpath --relative-to=engines/stable-diffusion.cpp/build/bin "$found")" engines/stable-diffusion.cpp/build/bin/sd-server
    echo "linked engines/stable-diffusion.cpp/build/bin/sd-server -> $found"
  fi
fi
