#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="$PWD/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"
cd "$(dirname "$0")/.."

echo "== SyMoNeuRaL doctor =="
echo "root: $(pwd)"
echo

check() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "OK: $1 -> $(command -v "$1")"
  else
    echo "MISSING: $1"
  fi
}

check python3
check pip
check cmake
check make
check nvidia-smi
check nvcc || true

echo
echo "== CUDA =="
nvidia-smi || true
nvcc --version || true

echo
echo "== Engine source dirs =="
[ -d engines/llama.cpp ] && echo "OK: engines/llama.cpp" || echo "MISSING: engines/llama.cpp"
[ -d engines/stable-diffusion.cpp ] && echo "OK: engines/stable-diffusion.cpp" || echo "MISSING: engines/stable-diffusion.cpp"

echo
echo "== Expected engine binaries =="
for f in \
  engines/llama.cpp/build/bin/llama-server \
  engines/llama.cpp/build/bin/llama-cli \
  engines/stable-diffusion.cpp/build/bin/sd-server \
  engines/stable-diffusion.cpp/build/examples/server/sd-server
do
  [ -e "$f" ] && echo "OK: $f" || echo "not built: $f"
done

echo
echo "== Models =="
find models -maxdepth 3 -type f \( -name '*.gguf' -o -name '*.safetensors' -o -name '*.ckpt' \) -printf '%p %k KB\n' 2>/dev/null || true

echo
echo "== Python import check =="
"$PYTHON_BIN" - <<'PY'
import app.main
import symon_tools
print("OK: app.main and symon_tools import")
PY
