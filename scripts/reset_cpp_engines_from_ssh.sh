#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:-/home/google}"
cd "$ROOT"

JOBS="${JOBS:-$(nproc)}"

LLAMA_REPO="git@github.com:ggml-org/llama.cpp.git"
SD_REPO="git@github.com:leejet/stable-diffusion.cpp.git"

LLAMA_DIR="$ROOT/engines/symon-llm.cpp"
SD_DIR="$ROOT/engines/symon-image.cpp"

echo "== Stop all running sessions/processes =="
tmux kill-server 2>/dev/null || true
pkill -f 'SyMoNeuRaL_ML/main.py|uvicorn.*SyMoNeuRaL|llama-server|symon-llm-server|sd-server|symon-image-server' || true
sleep 2

echo "== Scan home for old engine folders =="
SCAN_FILE="/tmp/symon_cpp_engine_dirs_to_delete.txt"

find "$HOME_DIR" \
  -type d \( \
    -name 'llama.cpp' -o \
    -name 'stable-diffusion.cpp' -o \
    -name 'stablediffusion.cpp' -o \
    -name 'stable_diffusion.cpp' \
  \) -prune -print | sort > "$SCAN_FILE"

echo
echo "These exact folders will be deleted:"
cat "$SCAN_FILE"
echo

if [ ! -s "$SCAN_FILE" ]; then
  echo "No old engine folders found."
else
  echo "Deleting old engine folders..."
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    case "$d" in
      "$HOME_DIR"/*)
        echo "sudo rm -rf $d"
        sudo rm -rf "$d"
        ;;
      *)
        echo "SKIP unsafe path: $d"
        ;;
    esac
  done < "$SCAN_FILE"
fi

echo
echo "== Recreate clean engines folder =="
mkdir -p "$ROOT/engines"

echo
echo "== Clone llama.cpp fresh using SSH =="
git clone --recursive "$LLAMA_REPO" "$LLAMA_DIR"
git -C "$LLAMA_DIR" submodule update --init --recursive

echo
echo "== Clone stable-diffusion.cpp fresh using SSH =="
git clone --recursive "$SD_REPO" "$SD_DIR"
git -C "$SD_DIR" submodule update --init --recursive

echo
echo "== Prepare requirements snapshots and Python envs =="
mkdir -p "$ROOT/requirements/.venvs"

collect_requirements() {
  local name="$1"
  local src="$2"
  local env="$ROOT/requirements/.venvs/$name"
  local list="$ROOT/requirements/${name}.requirements.files.txt"
  local combined="$ROOT/requirements/${name}.combined-requirements.txt"
  local freeze="$ROOT/requirements/${name}.freeze.txt"

  echo
  echo "== Find requirements for $name =="
  find "$src" -type f \( \
      -iname 'requirements*.txt' -o \
      -iname '*requirements*.txt' -o \
      -path '*/requirements/*.txt' \
    \) -print | sort > "$list"

  cat "$list"

  : > "$combined"
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    echo "# ===== $f =====" >> "$combined"
    cat "$f" >> "$combined"
    echo >> "$combined"
  done < "$list"

  python3 -m venv "$env"
  "$env/bin/python" -m pip install --upgrade pip setuptools wheel

  while IFS= read -r f; do
    [ -f "$f" ] || continue
    echo
    echo "pip install -r $f"
    "$env/bin/python" -m pip install -r "$f" || {
      echo "WARNING: requirements install failed for $f"
      echo "Continuing because some upstream optional requirement files are not meant for this CUDA build."
    }
  done < "$list"

  "$env/bin/python" -m pip freeze > "$freeze"
}

collect_requirements "llama.cpp" "$LLAMA_DIR"
collect_requirements "stable-diffusion.cpp" "$SD_DIR"

echo
echo "== Ensure stable-diffusion.cpp has ggml source if needed =="
if [ ! -d "$SD_DIR/ggml" ] && [ -d "$LLAMA_DIR/ggml" ]; then
  cp -a "$LLAMA_DIR/ggml" "$SD_DIR/ggml"
fi

echo
echo "== Configure llama.cpp CUDA build =="
cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" \
  -DGGML_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release

echo
echo "== Build llama.cpp server and cli =="
cmake --build "$LLAMA_DIR/build" --target llama-server -j"$JOBS"
cmake --build "$LLAMA_DIR/build" --target llama-cli -j"$JOBS" || true

echo
echo "== Configure stable-diffusion.cpp CUDA build =="
cmake -S "$SD_DIR" -B "$SD_DIR/build" \
  -DGGML_CUDA=ON \
  -DSD_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release

echo
echo "== Build stable-diffusion.cpp =="
cmake --build "$SD_DIR/build" -j"$JOBS"

echo
echo "== Locate stable-diffusion server binary =="
SD_BIN=""
for cand in \
  "$SD_DIR/build/bin/sd-server" \
  "$SD_DIR/build/sd-server" \
  "$SD_DIR/build/bin/stable-diffusion-server" \
  "$SD_DIR/build/stable-diffusion-server"
do
  if [ -x "$cand" ]; then
    SD_BIN="$cand"
    break
  fi
done

if [ -z "$SD_BIN" ]; then
  echo "ERROR: could not find stable-diffusion.cpp server binary."
  echo "Executable files found:"
  find "$SD_DIR/build" -type f -perm -111 | sort
  exit 1
fi

echo "SD_BIN=$SD_BIN"

echo
echo "== Install SyMoNeuRaL project binaries =="
mkdir -p "$ROOT/bin"

command cp -f "$LLAMA_DIR/build/bin/llama-server" "$ROOT/bin/symon-llm-server"
chmod +x "$ROOT/bin/symon-llm-server"

if [ -x "$LLAMA_DIR/build/bin/llama-cli" ]; then
  command cp -f "$LLAMA_DIR/build/bin/llama-cli" "$ROOT/bin/symon-llm-cli"
  chmod +x "$ROOT/bin/symon-llm-cli"
fi

command cp -f "$SD_BIN" "$ROOT/bin/symon-image-server"
chmod +x "$ROOT/bin/symon-image-server"

echo
echo "== Write status report =="
cat > "$ROOT/requirements/ENGINE_RESET_STATUS.txt" <<STATUS
SyMoNeuRaL C++ engine reset completed.

Deleted engine folders listed in:
  $SCAN_FILE

Fresh clones:
  $LLAMA_DIR
  $SD_DIR

SSH repos:
  $LLAMA_REPO
  $SD_REPO

Build dirs:
  $LLAMA_DIR/build
  $SD_DIR/build

Installed project binaries:
  bin/symon-llm-server
  bin/symon-llm-cli
  bin/symon-image-server

Requirement snapshots:
  requirements/llama.cpp.requirements.files.txt
  requirements/llama.cpp.combined-requirements.txt
  requirements/llama.cpp.freeze.txt
  requirements/stable-diffusion.cpp.requirements.files.txt
  requirements/stable-diffusion.cpp.combined-requirements.txt
  requirements/stable-diffusion.cpp.freeze.txt

Python envs, not for git commit:
  requirements/.venvs/llama.cpp
  requirements/.venvs/stable-diffusion.cpp
STATUS

cat "$ROOT/requirements/ENGINE_RESET_STATUS.txt"

echo
echo "== Git status =="
git status --short

echo
echo "== Done =="
echo "Start with:"
echo "  ./scripts/symon"
