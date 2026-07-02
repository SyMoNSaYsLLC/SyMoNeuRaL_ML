from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip(), "cmd": cmd}
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"not found: {cmd[0]}", "cmd": cmd}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": repr(exc), "cmd": cmd}


def cuda_toolchain_snapshot(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root)
    return {
        "nvidia_smi": _run(["nvidia-smi"], timeout=5),
        "nvcc": _run(["nvcc", "--version"], timeout=5),
        "cmake": _run(["cmake", "--version"], timeout=5),
        "python": _run(["python3", "--version"], timeout=5),
        "binaries": discover_binaries(root),
        "engine_sources": {
            "llama_cpp": str((root / "engines" / "llama.cpp").resolve()),
            "stable_diffusion_cpp": str((root / "engines" / "stable-diffusion.cpp").resolve()),
        },
    }


def discover_binaries(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root)
    candidates = {
        "llama_server": [
            root / "engines/llama.cpp/build/bin/llama-server",
            root / "engines/llama.cpp/build/bin/server",
            root / "engines/llama.cpp/build/bin/llama-cli",
        ],
        "llama_cli": [
            root / "engines/llama.cpp/build/bin/llama-cli",
            root / "engines/llama.cpp/build/bin/main",
        ],
        "sd_server": [
            root / "engines/stable-diffusion.cpp/build/bin/sd-server",
            root / "engines/stable-diffusion.cpp/build/examples/server/sd-server",
            root / "engines/stable-diffusion.cpp/build/bin/server",
        ],
        "sd_cli": [
            root / "engines/stable-diffusion.cpp/build/bin/sd",
            root / "engines/stable-diffusion.cpp/build/bin/sd-cli",
        ],
        "hf_to_gguf": [
            root / "engines/llama.cpp/convert_hf_to_gguf.py",
            root / "engines/llama.cpp/convert_hf_to_gguf_update.py",
        ],
    }
    out: dict[str, Any] = {}
    for name, paths in candidates.items():
        found = [str(p) for p in paths if p.exists()]
        out[name] = {"found": bool(found), "paths": found, "checked": [str(p) for p in paths]}
    return out


def model_inventory(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root)
    folders = {
        "llm": root / "models" / "llm",
        "sd": root / "models" / "sd",
        "adapters": root / "models" / "adapters",
    }
    exts = {".gguf", ".safetensors", ".ckpt", ".bin", ".pt", ".pth", ".onnx"}
    result: dict[str, Any] = {}
    for label, folder in folders.items():
        items = []
        if folder.exists():
            for p in sorted(folder.rglob("*")):
                if p.is_file() and p.suffix.lower() in exts:
                    items.append({
                        "path": str(p),
                        "name": p.name,
                        "size_mib": round(p.stat().st_size / (1024 * 1024), 2),
                        "suffix": p.suffix.lower(),
                    })
        result[label] = items
    return result


def build_command(target: str, cuda: bool = True, clean: bool = False) -> list[str]:
    target = target.lower().strip()
    if target in {"llama", "llama.cpp", "llama-cpp"}:
        return ["bash", "scripts/build_llama_cuda.sh"] + (["clean"] if clean else [])
    if target in {"sd", "stable", "stable-diffusion", "stable-diffusion.cpp", "stable_diffusion"}:
        return ["bash", "scripts/build_stable_diffusion_cuda.sh"] + (["clean"] if clean else [])
    if target in {"all", "both"}:
        return ["bash", "scripts/build_all_cuda.sh"] + (["clean"] if clean else [])
    raise ValueError(f"Unknown build target: {target}")


def run_build(root: Path | str, target: str, cuda: bool = True, clean: bool = False) -> dict[str, Any]:
    root = Path(root)
    cmd = build_command(target, cuda=cuda, clean=clean)
    p = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=int(os.getenv("SYMON_BUILD_TIMEOUT", "7200")))
    return {
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "cmd": cmd,
        "stdout": p.stdout[-12000:],
        "stderr": p.stderr[-12000:],
    }


def hf_to_gguf_command(root: Path | str, model_dir: str, outfile: str | None = None, outtype: str = "f16") -> list[str]:
    root = Path(root)
    converter = root / "engines" / "llama.cpp" / "convert_hf_to_gguf.py"
    if not converter.exists():
        raise FileNotFoundError(converter)
    cmd = ["python3", str(converter), model_dir, "--outtype", outtype]
    if outfile:
        cmd += ["--outfile", outfile]
    return cmd
