from __future__ import annotations
import argparse
import subprocess
import sys
from .paths import project_root

def run(script: str, extra: list[str]) -> int:
    root = project_root()
    return subprocess.call(["bash", str(root / "scripts" / script), *extra], cwd=root)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="symon-build", description="Build SyMoNeuRaL CUDA engines.")
    p.add_argument("target", nargs="?", default="all", choices=["all", "llama", "sd", "stable"])
    p.add_argument("args", nargs="*")
    ns = p.parse_args(argv)
    if ns.target == "llama":
        return run("build_llama_cuda.sh", ns.args)
    if ns.target in {"sd", "stable"}:
        return run("build_stable_diffusion_cuda.sh", ns.args)
    return run("build_all_cuda.sh", ns.args)

if __name__ == "__main__":
    raise SystemExit(main())
