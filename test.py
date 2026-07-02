#!/usr/bin/env python3
from __future__ import annotations

import argparse, contextlib, datetime as dt, json, os, subprocess, sys, time, urllib.request
from pathlib import Path
from typing import Any

REQUIRED_MODELS = [
    "models/llm/gemma-4-12b-it-Q4_K_M.gguf",
    "models/llm/qwen2.5-coder-1.5b-instruct-q8_0.gguf",
    "models/sd/v1-5-pruned-emaonly.safetensors",
]
REQUIRED_BINARIES = [
    "engines/llama.cpp/build/bin/llama-server",
    "engines/llama.cpp/build/bin/llama-cli",
    "engines/stable-diffusion.cpp/build/bin/sd-server",
]

class Tee:
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("w", encoding="utf-8", buffering=1)
        self.stdout = sys.__stdout__
    def write(self, data: str) -> int:
        self.stdout.write(data); self.file.write(data); return len(data)
    def flush(self) -> None:
        self.stdout.flush(); self.file.flush()
    def close(self) -> None:
        self.file.close()

def log_path(prefix: str, requested: str | None) -> Path:
    if requested:
        p = Path(requested)
    else:
        Path("logs").mkdir(exist_ok=True)
        p = Path("logs") / f"{prefix}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def ok(msg: str) -> None:
    print(f"OK: {msg}")

def fail(msg: str, failures: list[str]) -> None:
    print(f"FAIL: {msg}")
    failures.append(msg)

def http_json(url: str, timeout: float = 30) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))

def post_json(url: str, payload: dict[str, Any], timeout: float = 60) -> Any:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))

def check_path(path: str, failures: list[str], executable: bool = False) -> None:
    p = Path(path)
    if not p.exists():
        fail(f"missing {path}", failures); return
    if executable and not os.access(p, os.X_OK):
        fail(f"not executable {path}", failures); return
    ok(path)

def check_command(cmd: str, failures: list[str]) -> None:
    r = subprocess.run(["bash", "-lc", f"command -v {cmd}"], text=True, capture_output=True)
    ok(f"{cmd} -> {r.stdout.strip()}") if r.returncode == 0 else fail(f"{cmd} not found", failures)

def nvidia_smi() -> str:
    try:
        return subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits",
        ], text=True, stderr=subprocess.STDOUT, timeout=8).strip()
    except Exception as exc:
        return f"nvidia-smi unavailable: {exc!r}"

def wait_job(base: str, job_id: str, timeout: float = 180) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = http_json(f"{base}/api/v1/manager/jobs/{job_id}?include_image=false", timeout=15)
        if job.get("status") in {"done", "failed", "needs-review"}:
            return job
        time.sleep(1.5)
    raise TimeoutError(f"job {job_id} timed out")

def run(args: argparse.Namespace) -> int:
    failures: list[str] = []
    base = args.base.rstrip("/")
    print("== SyMoNeuRaL_ML smoke test ==")
    print("started:", dt.datetime.now().isoformat(timespec="seconds"))
    print("base:", base)
    print("log:", args.log_file)

    print("\n== Local files ==")
    for item in ["pyproject.toml", "config.yaml", "main.py"]:
        check_path(item, failures)
    for item in ["scripts/start_exclusive_16gb.sh", "scripts/doctor.sh"]:
        check_path(item, failures, executable=True)

    print("\n== Commands ==")
    for cmd in ["python3", "cmake", "make", "nvidia-smi", "nvcc"]:
        check_command(cmd, failures)

    print("\n== VRAM snapshot ==")
    print(nvidia_smi())

    print("\n== Engine binaries ==")
    for path in REQUIRED_BINARIES:
        check_path(path, failures, executable=True)

    print("\n== Models ==")
    for path in REQUIRED_MODELS:
        check_path(path, failures)

    print("\n== Python imports ==")
    try:
        import app.main  # noqa
        ok("import app.main")
    except Exception as exc:
        fail(f"import app.main: {exc!r}", failures)

    if not args.no_api:
        print("\n== API health ==")
        try:
            health = http_json(f"{base}/api/v1/health")
            print(json.dumps(health, indent=2)[:5000])
            ok("/api/v1/health") if health.get("ok") else fail("/api/v1/health returned ok=false", failures)
        except Exception as exc:
            fail(f"/api/v1/health: {exc!r}", failures)
        if not args.no_job:
            print("\n== Writer manager job ==")
            try:
                submitted = post_json(f"{base}/api/v1/manager/submit", {"route": "writer", "prompt": "Say SyMoNeuRaL smoke test passed in one short sentence."})
                job_id = submitted.get("id")
                if not job_id:
                    raise RuntimeError(f"no job id: {submitted}")
                ok(f"submitted writer job {job_id}")
                final = wait_job(base, job_id)
                print(json.dumps(final, indent=2)[:5000])
                ok("writer job completed") if final.get("status") == "done" else fail(f"writer job status {final.get('status')}", failures)
            except Exception as exc:
                fail(f"writer job: {exc!r}", failures)

    print("\n== Summary ==")
    json_path = Path(str(args.log_file).replace(".log", ".json"))
    json_path.write_text(json.dumps({"failures": failures, "failure_count": len(failures)}, indent=2), encoding="utf-8")
    if failures:
        for item in failures:
            print(f"- {item}")
        print(f"FAILED: {len(failures)} issue(s)")
        print("json_summary:", json_path)
        return 1
    print("PASSED")
    print("json_summary:", json_path)
    return 0

def main() -> int:
    p = argparse.ArgumentParser(description="SyMoNeuRaL_ML smoke test; creates logs automatically")
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--log-file")
    p.add_argument("--no-api", action="store_true")
    p.add_argument("--no-job", action="store_true")
    args = p.parse_args()
    path = log_path("test", args.log_file)
    args.log_file = str(path)
    tee = Tee(path)
    with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
        try:
            code = run(args)
        finally:
            print(f"\nLOG_FILE={path}")
            tee.flush()
    tee.close()
    print(f"Saved test log: {path}")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
