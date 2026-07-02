# GPU and Server Build Matrix

SyMoNeuRaL_ML is NVIDIA-first. Tune by model size, quantization, context, and GPU layers.

## Suggested profiles

| VRAM | Profile | Recommended starting point |
|---:|---|---|
| 8 GB | small/local test | `SYMON_CHAT_GPU_LAYERS=8 SYMON_CHAT_CTX=2048` |
| 12 GB | standard local | `SYMON_CHAT_GPU_LAYERS=12 SYMON_CHAT_CTX=2048` |
| 16 GB | recommended workstation | `SYMON_CHAT_GPU_LAYERS=16 SYMON_CHAT_CTX=2048` |
| 24 GB | performance workstation | `SYMON_CHAT_GPU_LAYERS=24 SYMON_CHAT_CTX=4096` |
| 48 GB+ | server | increase context/layers after watching `symon-vram` |

## Build requirements

```bash
sudo apt install build-essential cmake git python3 python3-venv python3-pip
```

NVIDIA stack:

```bash
nvidia-smi
nvcc --version
```

## Build

```bash
./scripts/build_all_cuda.sh
```

or:

```bash
cmake --preset cuda-release
cmake --build --preset cuda-all
```

## Watch memory

```bash
symon-vram
```

or:

```bash
watch -n 0.5 nvidia-smi
```

## Exclusive VRAM handoff

Idle:

```text
Gemma Writer Manager only
```

Heavy code:

```text
stop writer → start Qwen → build/test/package → stop Qwen → restart writer
```

Heavy image:

```text
stop writer → start Stable Diffusion → render → stop SD → restart writer
```
