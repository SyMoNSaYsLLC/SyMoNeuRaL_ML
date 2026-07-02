#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p "$PWD/data/symoneural_handoff_jobs" "$PWD/data/symoneural_coder_jobs" "$PWD/logs" "$PWD/models"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .

mkdir -p engines models/llm models/sd models/adapters logs bin data/symoneural_handoff_jobs data/symoneural_coder_jobs

cat <<'MSG'
Install complete.

Next steps:
  1) Build CUDA engines:
       ./scripts/build_all_cuda.sh

  2) Install PATH commands:
       ./scripts/install_path_tools.sh
       export PATH="$HOME/.local/bin:$PATH"

  3) Put models here:
       models/llm/gemma-4-12b-it-Q4_K_M.gguf
       models/llm/qwen2.5-coder-1.5b-instruct-q8_0.gguf
       models/sd/v1-5-pruned-emaonly.safetensors

  4) Start:
       ./scripts/start_exclusive_16gb.sh
       # or:
       symon-server

Tools:
  symon-cli health
  symon-cli vram
  symon-build all
  symon-hf_to_gguf /path/to/hf-model --outfile models/llm/model.gguf
MSG
