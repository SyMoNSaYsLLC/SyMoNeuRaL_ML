from __future__ import annotations
import subprocess, time, argparse

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="symon-vram")
    p.add_argument("-n", "--interval", type=float, default=0.5)
    ns = p.parse_args(argv)
    try:
        while True:
            subprocess.call(["nvidia-smi"])
            time.sleep(ns.interval)
    except KeyboardInterrupt:
        return 0
