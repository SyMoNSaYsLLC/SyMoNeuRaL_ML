#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "clean" ]; then
  sudo rm -rf engines/symon-image.cpp/build
fi

if [ ! -d engines/symon-image.cpp ]; then
  echo "Missing engines/symon-image.cpp. Copy or clone stable-diffusion.cpp there." >&2
  exit 2
fi

mkdir -p engines/symon-image.cpp/build
cmake -S engines/symon-image.cpp -B engines/symon-image.cpp/build \
  -DCMAKE_BUILD_TYPE="${CMAKE_BUILD_TYPE:-Release}" \
  -DSD_CUDA="${SD_CUDA:-ON}" \
  -DGGML_CUDA="${GGML_CUDA:-ON}" \
  -DSD_BUILD_SERVER=ON \
  -DSD_BUILD_EXAMPLES=ON \
  -DSD_BUILD_TESTS=OFF

cmake --build engines/symon-image.cpp/build --config "${CMAKE_BUILD_TYPE:-Release}" -j "${SYMON_BUILD_JOBS:-$(nproc)}"

echo
echo "stable-diffusion.cpp CUDA build complete."
echo "Expected binaries:"
find engines/symon-image.cpp/build -maxdepth 5 -type f \( -name 'sd-server' -o -name 'sd' -o -name 'stable-diffusion' \) -print

# ensure config.yaml path works even if upstream puts sd-server under examples/server
mkdir -p engines/symon-image.cpp/build/bin
if [ ! -e bin/symon-image-server ]; then
  found="$(find engines/symon-image.cpp/build -type f -name 'sd-server' | head -n1 || true)"
  if [ -n "$found" ]; then
    ln -sf "$(realpath --relative-to=engines/symon-image.cpp/build/bin "$found")" bin/symon-image-server
    echo "linked bin/symon-image-server -> $found"
  fi
fi
