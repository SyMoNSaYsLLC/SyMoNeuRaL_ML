# SyMoNeuRaL CUDA and Model Tools

This project now vendors `llama.cpp` and `stable-diffusion.cpp` under `engines/` and exposes project-level build, runtime, conversion, VRAM, and model inventory tools.

## Source layout

```text
engines/
├── llama.cpp/
└── stable-diffusion.cpp/
```

The active production app remains Python/FastAPI, but model execution is handled by the CUDA-capable C/C++ engines. This mirrors the upstream projects instead of trying to rewrite CUDA inference in Python.

## Build with scripts

```bash
./scripts/build_llama_cuda.sh
./scripts/build_stable_diffusion_cuda.sh
./scripts/build_all_cuda.sh
```

Clean rebuild:

```bash
./scripts/build_all_cuda.sh clean
```

## Build with CMake presets

```bash
cmake --preset cuda-release
cmake --build --preset cuda-all
```

Individual targets:

```bash
cmake --build --preset cuda-llama
cmake --build --preset cuda-sd
```

## Install PATH commands

```bash
./scripts/install_path_tools.sh
export PATH="$HOME/.local/bin:$PATH"
```

Add this permanently:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Commands

```text
symon-server       Start the production FastAPI app
symon-web          Open http://127.0.0.1:8000
symon-cli          API CLI: health, vram, catalog, ask, jobs
symon-build        Build CUDA engines: all, llama, sd
symon-hf_to_gguf   Wrap llama.cpp convert_hf_to_gguf.py
symon-vram         Watch nvidia-smi
```

After a successful engine build, these binary symlinks are also created when available:

```text
symon-llama-server
symon-llama-cli
symon-sd-server
```

## Convert Hugging Face to GGUF

```bash
symon-hf_to_gguf /path/to/hf-model --outfile models/llm/my-model.gguf --outtype f16
```

Equivalent script:

```bash
./scripts/convert_hf_to_gguf.sh /path/to/hf-model --outfile models/llm/my-model.gguf --outtype f16
```

## Backend tool API

```text
GET  /api/v1/tools/cuda
GET  /api/v1/tools/models
POST /api/v1/tools/build
POST /api/v1/tools/convert/hf-to-gguf
```

Build request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tools/build \
  -H 'Content-Type: application/json' \
  -d '{"target":"all","clean":false}'
```

HF to GGUF command plan:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tools/convert/hf-to-gguf \
  -H 'Content-Type: application/json' \
  -d '{"model_dir":"/path/to/hf-model","outfile":"models/llm/model.gguf","outtype":"f16"}'
```

Run conversion as a background job:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tools/convert/hf-to-gguf \
  -H 'Content-Type: application/json' \
  -d '{"model_dir":"/path/to/hf-model","outfile":"models/llm/model.gguf","outtype":"f16","run":true}'
```

## CUDA notes

The build scripts use the current upstream CMake flags:

```text
llama.cpp:
  -DGGML_CUDA=ON
  -DLLAMA_BUILD_SERVER=ON
  -DLLAMA_BUILD_TOOLS=ON

stable-diffusion.cpp:
  -DSD_CUDA=ON
  -DGGML_CUDA=ON
  -DSD_BUILD_SERVER=ON
  -DSD_BUILD_EXAMPLES=ON
```

If your upstream checkout changes options later, update only the build scripts and CMake presets. The FastAPI app reads binaries through `config.yaml`.
