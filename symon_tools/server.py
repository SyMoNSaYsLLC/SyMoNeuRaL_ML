from __future__ import annotations
import os
import subprocess
import sys
from .paths import project_root

def main() -> int:
    root = project_root()
    os.chdir(root)
    env = os.environ.copy()
    if "SYMON_CHAT_GPU_LAYERS" not in env:
        env["SYMON_CHAT_GPU_LAYERS"] = "16"
    if "SYMON_CHAT_CTX" not in env:
        env["SYMON_CHAT_CTX"] = "2048"
    return subprocess.call([sys.executable, "main.py"], env=env)

if __name__ == "__main__":
    raise SystemExit(main())
