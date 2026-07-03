#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JOBS="${JOBS:-$(nproc)}"
NO_PUSH="${NO_PUSH:-0}"

LLM_OLD="engines/llama.cpp"
LLM_NEW="engines/symon-llm.cpp"
IMG_OLD="engines/stable-diffusion.cpp"
IMG_NEW="engines/symon-image.cpp"

die(){ echo "ERROR: $*" >&2; exit 1; }
[ -f pyproject.toml ] || die "run from SyMoNeuRaL_ML repo"
[ -d engines ] || die "missing engines/"

echo "== Stop running engines =="
pkill -f 'SyMoNeuRaL_ML/main.py|uvicorn.*SyMoNeuRaL|llama-server|symon-llm-server|sd-server|symon-image-server' || true
sleep 1

echo "== Move source trees to SyMoNeuRaL-owned names =="
if [ -d "$LLM_OLD" ] && [ ! -d "$LLM_NEW" ]; then
  mv "$LLM_OLD" "$LLM_NEW"
elif [ -d "$LLM_NEW" ] && [ ! -d "$LLM_OLD" ]; then
  echo "already moved: $LLM_NEW"
else
  [ -d "$LLM_NEW" ] || die "missing $LLM_OLD or $LLM_NEW"
  [ ! -d "$LLM_OLD" ] || die "both $LLM_OLD and $LLM_NEW exist; clean that first"
fi

if [ -d "$IMG_OLD" ] && [ ! -d "$IMG_NEW" ]; then
  mv "$IMG_OLD" "$IMG_NEW"
elif [ -d "$IMG_NEW" ] && [ ! -d "$IMG_OLD" ]; then
  echo "already moved: $IMG_NEW"
else
  [ -d "$IMG_NEW" ] || die "missing $IMG_OLD or $IMG_NEW"
  [ ! -d "$IMG_OLD" ] || die "both $IMG_OLD and $IMG_NEW exist; clean that first"
fi

echo "== Clean old build dirs =="
sudo rm -rf "$LLM_NEW/build" "$IMG_NEW/build"

echo "== Patch repo references and engine branding =="
python3 - <<'PY'
from pathlib import Path

# Patch repo references.
repo_pairs = [
    ("engines/llama.cpp", "engines/symon-llm.cpp"),
    ("engines/stable-diffusion.cpp", "engines/symon-image.cpp"),
    ("llama.cpp/build", "symon-llm.cpp/build"),
    ("stable-diffusion.cpp/build", "symon-image.cpp/build"),
]
skip = {".git", ".venv", "__pycache__", "models", "logs", "data", ".symon_update"}
exts = {".py",".sh",".md",".txt",".yaml",".yml",".toml",".json",".cmake",".ini",".conf",".service",".cpp",".hpp",".h",".c",".cc",".cxx",".html",".css",".js"}

for p in Path(".").rglob("*"):
    if not p.is_file() or any(part in skip for part in p.parts):
        continue
    if p.suffix not in exts and p.name not in {"Makefile","Dockerfile","CMakeLists.txt"}:
        continue
    try:
        s = p.read_text()
    except UnicodeDecodeError:
        continue
    old = s
    for a,b in repo_pairs:
        s = s.replace(a,b)
    if s != old:
        p.write_text(s)
        print("patched refs", p)

# Brand copied LLM engine. This patches definitions and callers together.
llm = Path("engines/symon-llm.cpp")
llm_pairs = [
    ("llama_server", "symon_llm_server"),
    ("llama-server", "symon-llm-server"),
    ("llama server", "symon llm server"),
    ("llama.cpp server", "SyMoNeuRaL LLM server"),
]
for p in llm.rglob("*"):
    if not p.is_file() or p.suffix not in {".cpp",".hpp",".h",".c",".cc",".cxx",".cmake",".txt"}:
        continue
    try:
        s = p.read_text()
    except UnicodeDecodeError:
        continue
    old = s
    for a,b in llm_pairs:
        s = s.replace(a,b)
    if s != old:
        p.write_text(s)
        print("branded llm", p)

# Brand copied image engine.
img = Path("engines/symon-image.cpp")
img_pairs = [
    ("stable-diffusion.cpp", "symon-image.cpp"),
    ("sd-server", "symon-image-server"),
    ("stable diffusion server", "symon image server"),
    ("Stable Diffusion", "SyMoNeuRaL Image"),
]
for p in img.rglob("*"):
    if not p.is_file() or p.suffix not in {".cpp",".hpp",".h",".c",".cc",".cxx",".cmake",".txt",".md"}:
        continue
    try:
        s = p.read_text()
    except UnicodeDecodeError:
        continue
    old = s
    for a,b in img_pairs:
        s = s.replace(a,b)
    if s != old:
        p.write_text(s)
        print("branded image", p)
PY

echo "== Ensure image engine has ggml =="
if [ ! -d "$IMG_NEW/ggml" ] && [ -d "$LLM_NEW/ggml" ]; then
  cp -a "$LLM_NEW/ggml" "$IMG_NEW/ggml"
fi

echo "== Build Symon LLM engine =="
cmake -S "$LLM_NEW" -B "$LLM_NEW/build" -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
if cmake --build "$LLM_NEW/build" --target symon-llm-server -j"$JOBS"; then
  LLM_BIN="$LLM_NEW/build/bin/symon-llm-server"
else
  cmake --build "$LLM_NEW/build" --target llama-server -j"$JOBS"
  LLM_BIN="$LLM_NEW/build/bin/llama-server"
fi
[ -x "$LLM_BIN" ] || die "missing LLM binary: $LLM_BIN"

echo "== Build Symon image engine =="
cmake -S "$IMG_NEW" -B "$IMG_NEW/build" -DGGML_CUDA=ON -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release
if cmake --build "$IMG_NEW/build" --target symon-image-server -j"$JOBS"; then
  IMG_BIN="$IMG_NEW/build/bin/symon-image-server"
elif cmake --build "$IMG_NEW/build" --target sd-server -j"$JOBS"; then
  IMG_BIN="$IMG_NEW/build/bin/sd-server"
else
  cmake --build "$IMG_NEW/build" -j"$JOBS"
  IMG_BIN=""
  for c in "$IMG_NEW/build/bin/symon-image-server" "$IMG_NEW/build/bin/sd-server" "$IMG_NEW/build/symon-image-server" "$IMG_NEW/build/sd-server"; do
    [ -x "$c" ] && IMG_BIN="$c" && break
  done
fi
[ -n "${IMG_BIN:-}" ] && [ -x "$IMG_BIN" ] || die "missing image binary"

echo "== Install project binaries =="
mkdir -p bin
command cp -f "$LLM_BIN" bin/symon-llm-server
command cp -f "$IMG_BIN" bin/symon-image-server
chmod +x bin/symon-llm-server bin/symon-image-server
if [ -x "$LLM_NEW/build/bin/llama-cli" ]; then
  command cp -f "$LLM_NEW/build/bin/llama-cli" bin/symon-llm-cli
  chmod +x bin/symon-llm-cli
fi

echo "== Force runtime to project binaries =="
python3 - <<'PY'
from pathlib import Path
for p in [Path("config.yaml"), *Path("scripts").glob("*.sh"), *Path("app").rglob("*.py")]:
    if not p.exists() or not p.is_file(): continue
    try: s = p.read_text()
    except UnicodeDecodeError: continue
    old = s
    repls = [
        ("./engines/symon-llm.cpp/build/bin/llama-server", "./bin/symon-llm-server"),
        ("engines/symon-llm.cpp/build/bin/llama-server", "bin/symon-llm-server"),
        ("./engines/symon-llm.cpp/build/bin/symon-llm-server", "./bin/symon-llm-server"),
        ("engines/symon-llm.cpp/build/bin/symon-llm-server", "bin/symon-llm-server"),
        ("./engines/symon-image.cpp/build/bin/sd-server", "./bin/symon-image-server"),
        ("engines/symon-image.cpp/build/bin/sd-server", "bin/symon-image-server"),
        ("./engines/symon-image.cpp/build/bin/symon-image-server", "./bin/symon-image-server"),
        ("engines/symon-image.cpp/build/bin/symon-image-server", "bin/symon-image-server"),
    ]
    for a,b in repls: s = s.replace(a,b)
    if s != old:
        p.write_text(s)
        print("runtime patched", p)
PY

mkdir -p docs
cat > docs/SYMON_OWNED_ENGINES.md <<'EOF'
# SyMoNeuRaL-Owned Engine Sources

Project-owned modified engine source trees:

- `engines/symon-llm.cpp`
- `engines/symon-image.cpp`

Canonical runtime binaries:

- `bin/symon-llm-server`
- `bin/symon-image-server`

Canonical startup:

```bash
./scripts/symon
```

The copied source trees preserve original license/attribution files.
EOF

echo "== Verify strings =="
strings bin/symon-llm-server | grep -E 'symon_llm_server|llama_server|symon-llm-server|llama-server' | head -30 || true
strings bin/symon-image-server | grep -E 'symon-image|sd-server|stable-diffusion' | head -30 || true

echo "== Commit and push =="
git status --short
git add engines/symon-llm.cpp engines/symon-image.cpp bin/symon-llm-server bin/symon-image-server bin/symon-llm-cli app scripts config config.yaml docs README.md pyproject.toml CMakeLists.txt Makefile 2>/dev/null || true
git add -u engines/llama.cpp engines/stable-diffusion.cpp 2>/dev/null || true
if git diff --cached --quiet; then
  echo "No staged changes."
else
  git commit -m "vendor: migrate engines to SyMoNeuRaL-owned sources"
fi
if [ "$NO_PUSH" != "1" ]; then git push origin main; fi

echo "== Done =="
echo "Start: ./scripts/symon"
echo "Check: pgrep -af 'symon-llm-server|symon-image-server|llama-server|sd-server'"
