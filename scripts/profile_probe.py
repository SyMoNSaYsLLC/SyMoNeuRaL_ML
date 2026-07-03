#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow this script to run directly as:
#   python scripts/profile_probe.py ...
# without requiring PYTHONPATH=. from the user.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Re-exec through repo venv when available.
for rel in (".venv/bin/python", ".venv/bin/python3"):
    venv_py = ROOT / rel
    if venv_py.exists() and os.access(venv_py, os.X_OK) and Path(sys.executable).resolve() != venv_py.resolve():
        os.execv(str(venv_py), [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])

from app.services.symon_adaptive_profiles import choose_profile, profile_dict


def main() -> int:
    p = argparse.ArgumentParser(description="Inspect SyMoNeuRaL adaptive profile selection")
    p.add_argument("prompt", nargs="+")
    p.add_argument("--route", default="writer", choices=["writer", "code", "image"])
    p.add_argument("--phase", default="")
    args = p.parse_args()
    prompt = " ".join(args.prompt)
    print(json.dumps(profile_dict(choose_profile(args.route, prompt, prompt, {}, args.phase)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
