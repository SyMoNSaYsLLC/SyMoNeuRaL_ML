from __future__ import annotations
import argparse
import subprocess
import sys
from .paths import project_root

def main(argv: list[str] | None = None) -> int:
    root = project_root()
    converter = root / "engines" / "llama.cpp" / "convert_hf_to_gguf.py"
    p = argparse.ArgumentParser(prog="symon-hf_to_gguf", description="Wrapper around llama.cpp convert_hf_to_gguf.py")
    p.add_argument("model_dir", help="Hugging Face model directory")
    p.add_argument("--outfile", default=None)
    p.add_argument("--outtype", default="f16", choices=["f32", "f16", "bf16", "q8_0", "tq1_0", "tq2_0", "auto"])
    p.add_argument("extra", nargs=argparse.REMAINDER)
    ns = p.parse_args(argv)
    if not converter.exists():
        print(f"Missing converter: {converter}", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(converter), ns.model_dir, "--outtype", ns.outtype]
    if ns.outfile:
        cmd += ["--outfile", ns.outfile]
    cmd += ns.extra
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=root)

if __name__ == "__main__":
    raise SystemExit(main())
