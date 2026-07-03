#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
