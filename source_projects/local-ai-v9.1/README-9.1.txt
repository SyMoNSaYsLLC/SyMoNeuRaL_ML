SyMoNeuRaL v9.1

Includes v9 UI upgrade plus:
- source-inspired canonical API catalog
- unified /api/v1/generate
- /api/v1/tools/vram nvidia-smi helper
- /api/v1/tools/fine-tune-plan LoRA/PEFT planning helper
- frontend helper chips for writer/code/image prompts
- docs and scripts copied into ~/local-ai

Install:
  cd ~/Downloads/local-ai-v9.1
  ./install_9_1.sh ~/local-ai

Run:
  cd ~/local-ai
  source .venv/bin/activate
  SYMON_CHAT_GPU_LAYERS=16 SYMON_CHAT_CTX=2048 python main.py
