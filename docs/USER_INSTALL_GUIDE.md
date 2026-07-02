# User Install Guide

This guide is for users installing and running SyMoNeuRaL_ML on an NVIDIA GPU server or workstation.

## 1. System requirements

Recommended packages:

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3 python3-venv python3-pip curl ca-certificates
```

NVIDIA checks:

```bash
nvidia-smi
nvcc --version
```

## 2. Install Python environment

From the project directory:

```bash
./scripts/install.sh
./scripts/doctor.sh
```

## 3. Build CUDA engines

```bash
./scripts/build_all_cuda.sh
```

or:

```bash
cmake --preset cuda-release
cmake --build --preset cuda-all
```

## 4. Install PATH tools

```bash
./scripts/install_path_tools.sh
export PATH="$HOME/.local/bin:$PATH"
```

Optional permanent shell setup:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 5. Start the server

```bash
./scripts/start_exclusive_16gb.sh
```

or:

```bash
symon-server
```

Open:

```text
http://127.0.0.1:8000
```

## 6. Monitor VRAM

```bash
symon-vram
```

or:

```bash
watch -n 0.5 nvidia-smi
```
