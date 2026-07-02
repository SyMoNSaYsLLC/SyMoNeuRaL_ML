SyMoNeuRaL UI Upgrade v9

This is a visual/UX upgrade only. It keeps the v8 backend and service behavior.

Install:
  cd ~/Downloads/local-ai-ui-upgrade-v9
  ./install_ui.sh ~/local-ai

Run:
  cd ~/local-ai
  source .venv/bin/activate
  SYMON_CHAT_GPU_LAYERS=16 SYMON_CHAT_CTX=2048 python main.py

Then hard refresh the browser with Ctrl+Shift+R.
