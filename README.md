# SyMoNeuRaL_ML

**NVIDIA-focused local 3-model MoE web server with CUDA model tools, llama.cpp, stable-diffusion.cpp, FastAPI, and exclusive VRAM handoff.**

Version: `1.5.2-install-doctor-docs-hotfix`

SyMoNeuRaL_ML is a local/private ML server for NVIDIA GPU systems. It provides a production-style web UI, API, CUDA engine builds, model conversion tools, VRAM monitoring, and a 3-model handoff workflow.

## What it includes

- **Gemma Writer Manager** — resident visible writer/planner/decision model.
- **Qwen Code Worker** — hidden background coding/building/testing worker.
- **Stable Diffusion Worker** — hidden image generation worker through `stable-diffusion.cpp`.
- **Exclusive VRAM handoff** — only the manager stays loaded at idle; code/image workers receive the GPU during heavy jobs.
- **CUDA/model tools** — project-level build, conversion, VRAM, and model inventory commands.
- **FastAPI control plane** — current backend with a PHP migration bridge documented for later.

## What this project is for

SyMoNeuRaL_ML is designed for local/private AI servers running NVIDIA GPUs. It wraps CUDA-capable C/C++ inference engines with a web/API layer and provides PATH commands for model conversion, server launch, VRAM monitoring, engine builds, and handoff jobs.

The project vendors:

```text
engines/llama.cpp
engines/stable-diffusion.cpp
```

and exposes them through:

```text
symon-server
symon-web
symon-cli
symon-build
symon-hf_to_gguf
symon-vram
```

## Production architecture

### Idle state

```text
User → Gemma Writer Manager
```

Only the Writer Manager stays resident so normal questions and planning keep VRAM low.

### Code handoff

```text
User
 → Gemma Writer Manager cleans/specs request
 → Writer Manager stops
 → Qwen Code Worker starts with the GPU available
 → Qwen builds/tests under the project data folder, usually `data/symoneural_handoff_jobs`
 → Qwen returns a .tar.gz artifact
 → Qwen stops
 → Writer Manager restarts
 → Writer Manager assesses
 → approved artifact goes to user
```

### Image handoff

```text
User
 → Gemma Writer Manager cleans prompt
 → Writer Manager stops
 → Stable Diffusion Worker starts with the GPU available
 → image renders
 → Stable Diffusion stops
 → Writer Manager restarts
 → Writer Manager assesses
 → approved image goes to user
```

The user sees this during heavy handoff jobs:

```text
This task requires a lot of processing power, but please wait — your code/image is coming soon.
```

## GPU/server support

This project is NVIDIA-first. Performance depends on VRAM, CUDA toolkit, driver, model quantization, context size, and GPU layer offload.

| Server/GPU class | Suggested use | Starting settings |
|---|---|---|
| 8 GB NVIDIA | small Qwen/code models, SD 1.5, low context | `SYMON_CHAT_GPU_LAYERS=8`, `SYMON_CHAT_CTX=2048` |
| 12 GB NVIDIA | balanced writer + code handoff, SD 1.5 | `SYMON_CHAT_GPU_LAYERS=12`, `SYMON_CHAT_CTX=2048` |
| 16 GB NVIDIA | recommended local workstation profile | `SYMON_CHAT_GPU_LAYERS=16`, `SYMON_CHAT_CTX=2048` |
| 24 GB NVIDIA | larger writer context and stronger image/code handoffs | `SYMON_CHAT_GPU_LAYERS=24`, `SYMON_CHAT_CTX=4096` |
| 48 GB+ NVIDIA | bigger local models, higher context, larger SD workloads | tune per model with `symon-vram` |

For a 16 GB NVIDIA workstation:

```bash
SYMON_CHAT_GPU_LAYERS=16 SYMON_CHAT_CTX=2048 python main.py
```

## Quick start

From the project directory:

```bash
./scripts/install.sh
./scripts/doctor.sh
./scripts/build_all_cuda.sh
./scripts/install_path_tools.sh

export PATH="$HOME/.local/bin:$PATH"
```

Start the server:

```bash
symon-server
```

or:

```bash
./scripts/start_exclusive_16gb.sh
```

Open:

```text
http://127.0.0.1:8000
```

## Project data folders

The default install uses project-local data folders so normal users do not need write access to `/mnt`:

```text
data/symoneural_handoff_jobs
data/symoneural_coder_jobs
data/rag
data/fine_tune
logs
models
```

Advanced users can point handoff work elsewhere with environment variables, but the default user install should stay inside the project directory.

## Clean CUDA rebuild after zip extraction / clock skew

If the CUDA build shows warnings like:

```text
Clock skew detected. Your build may be incomplete.
```

normalize the vendored engine timestamps before rebuilding:

```bash
find engines/llama.cpp engines/stable-diffusion.cpp -exec touch {} +

./scripts/install.sh
./scripts/doctor.sh
./scripts/build_all_cuda.sh
```

This is mainly needed after extracting source archives whose file timestamps are ahead of the system clock.

## Doctor/import troubleshooting

`doctor.sh` should use the project virtual environment when `.venv` exists. If Python import checks fail even though install succeeded, rerun:

```bash
source .venv/bin/activate
./scripts/doctor.sh
```

Then confirm:

```bash
which python
python -c "import fastapi, anyio; print('imports ok')"
```

## PATH commands

After:

```bash
./scripts/install_path_tools.sh
export PATH="$HOME/.local/bin:$PATH"
```

you get:

```text
symon-server       Start the production FastAPI app
symon-web          Open the web UI
symon-cli          API CLI: health, vram, catalog, ask, jobs
symon-build        Build CUDA engines: all, llama, sd
symon-hf_to_gguf   Convert Hugging Face models to GGUF through llama.cpp
symon-vram         Watch nvidia-smi
```

After engine builds, the installer also links engine binaries when available:

```text
symon-llama-server
symon-llama-cli
symon-sd-server
```

## Build engines

Script build:

```bash
symon-build all
symon-build llama
symon-build sd
```

Direct scripts:

```bash
./scripts/build_llama_cuda.sh
./scripts/build_stable_diffusion_cuda.sh
./scripts/build_all_cuda.sh
```

CMake presets:

```bash
cmake --preset cuda-release
cmake --build --preset cuda-all
```

CPU fallback preset:

```bash
cmake --preset cpu-release
```

## Convert Hugging Face to GGUF

```bash
symon-hf_to_gguf /path/to/hf-model \
  --outfile models/llm/my-model.gguf \
  --outtype f16
```

Equivalent script:

```bash
./scripts/convert_hf_to_gguf.sh /path/to/hf-model \
  --outfile models/llm/my-model.gguf \
  --outtype f16
```

## Main API

```text
GET  /api/v1/catalog
GET  /api/v1/health
GET  /api/v1/tools/vram
GET  /api/v1/tools/cuda
GET  /api/v1/tools/models

POST /api/v1/manager/submit
GET  /api/v1/manager/jobs
GET  /api/v1/manager/jobs/{job_id}
GET  /api/v1/manager/jobs/{job_id}/artifact

POST /api/v1/tools/build
POST /api/v1/tools/convert/hf-to-gguf
```

Legacy compatibility routes remain:

```text
POST /api/v1/generate
POST /api/v1/chat/completions
POST /api/v1/images/generations
POST /api/v1/coder/background
```

## Model placement

Expected active model paths:

```text
models/llm/gemma-4-12b-it-Q4_K_M.gguf
models/llm/qwen2.5-coder-1.5b-instruct-q8_0.gguf
models/sd/v1-5-pruned-emaonly.safetensors
```

You can change these in:

```text
config.yaml
```

## Production notes

Python/FastAPI is the current control plane. The project includes `php_bridge/` and `docs/PHP_MIGRATION_NOTES.md` so the web/API control layer can migrate toward PHP later without changing the CUDA inference engines.

The recommended production split is:

```text
C/C++ CUDA engines: inference performance
Python/FastAPI now: orchestration/API/workers/tools
PHP later: production web/API control plane
```

## Source layout

Reference source trees, upstream engine sources, and migrated project references may be preserved under:

```text
source_projects/
```

Active production code is under:

```text
app/
frontend/
helpers/
scripts/
deploy/
symon_tools/
engines/
```

## RTX 5070 Ti Permanent 14-15GB VRAM Profile

Canonical startup:

```bash
./scripts/symon
```

This sources `config/rtx5070ti_14_15gb.env` and targets 14000-15360 MiB total GPU memory on the RTX 5070 Ti 16GB card. Do not revert normal startup to the old ~8GB conservative llama-server profile.
