#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _venv_python() -> Path | None:
    for rel in (".venv/bin/python", ".venv/bin/python3"):
        p = ROOT / rel
        if p.exists() and os.access(p, os.X_OK):
            return p.resolve()
    return None

VENV_PY = _venv_python()
if VENV_PY is not None and Path(sys.executable).resolve() != VENV_PY:
    os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])

import argparse
import contextlib
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_MODELS = [
    "models/llm/gemma-4-12b-it-Q4_K_M.gguf",
    "models/llm/qwen2.5-coder-1.5b-instruct-q8_0.gguf",
    "models/sd/v1-5-pruned-emaonly.safetensors",
]
REQUIRED_BINARIES = [
    "engines/symon-llm.cpp/build/bin/llama-server",
    "engines/symon-llm.cpp/build/bin/llama-cli",
    "engines/symon-image.cpp/build/bin/sd-server",
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

class ResourceMonitor:
    def __init__(self, prefix: str, interval: float = 1.0):
        (ROOT / "logs").mkdir(exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_path = ROOT / "logs" / f"{prefix}_{stamp}_metrics.csv"
        self.summary_path = ROOT / "logs" / f"{prefix}_{stamp}_metrics_summary.json"
        self.proc: subprocess.Popen[str] | None = None
        self.interval = interval
    def start(self) -> None:
        cmd = [sys.executable, str(ROOT / "resource_monitor.py"), "--out", str(self.csv_path), "--summary", str(self.summary_path), "--interval", str(self.interval)]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    def stop(self) -> None:
        if not self.proc:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=8)
    def summary(self) -> dict[str, Any]:
        try:
            return json.loads(self.summary_path.read_text())
        except Exception:
            return {}

def log_path(prefix: str, requested: str | None) -> Path:
    if requested:
        p = Path(requested)
    else:
        (ROOT / "logs").mkdir(exist_ok=True)
        p = ROOT / "logs" / f"{prefix}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    p = ROOT / path
    if not p.exists():
        fail(f"missing {path}", failures); return
    if executable and not os.access(p, os.X_OK):
        fail(f"not executable {path}", failures); return
    ok(path)

def check_command(cmd: str, failures: list[str]) -> None:
    r = subprocess.run(["bash", "-lc", f"command -v {cmd}"], text=True, capture_output=True)
    ok(f"{cmd} -> {r.stdout.strip()}") if r.returncode == 0 else fail(f"{cmd} not found", failures)

def wait_job(base: str, job_id: str, timeout: float = 180) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = http_json(f"{base}/api/v1/manager/jobs/{job_id}?include_image=false", timeout=15)
        if job.get("status") in {"done", "failed", "needs-review"}:
            return job
        time.sleep(1.5)
    raise TimeoutError(f"job {job_id} timed out")

def run(args: argparse.Namespace, monitor: ResourceMonitor | None) -> int:
    failures: list[str] = []
    warnings: list[str] = []
    base = args.base.rstrip("/")

    print("== SyMoNeuRaL_ML smoke test ==")
    print("started:", dt.datetime.now().isoformat(timespec="seconds"))
    print("root:", ROOT)
    print("python:", sys.executable)
    print("base:", base)
    print("log:", args.log_file)
    if monitor:
        print("metrics_csv:", monitor.csv_path)
        print("metrics_summary:", monitor.summary_path)

    print("\n== Local files ==")
    for item in ["pyproject.toml", "config.yaml", "main.py"]:
        check_path(item, failures)
    for item in ["scripts/start_exclusive_16gb.sh", "scripts/doctor.sh"]:
        check_path(item, failures, executable=True)

    print("\n== Commands ==")
    for cmd in ["python3", "cmake", "make", "nvidia-smi", "nvcc"]:
        check_command(cmd, failures)

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

    server_up = False
    if not args.no_api:
        print("\n== API health ==")
        try:
            health = http_json(f"{base}/api/v1/health")
            print(json.dumps(health, indent=2)[:5000])
            if health.get("ok"):
                ok("/api/v1/health")
                server_up = True
            else:
                fail("/api/v1/health returned ok=false", failures)
        except urllib.error.URLError as exc:
            msg = f"server is not reachable at {base}; start it with ./scripts/start_exclusive_16gb.sh"
            if args.require_server:
                fail(f"/api/v1/health: {exc!r}; {msg}", failures)
            else:
                print(f"SKIP: {msg}")
                warnings.append(msg)

        if not args.no_job:
            print("\n== Writer manager job ==")
            if not server_up:
                msg = "writer job skipped because server is not reachable"
                print(f"SKIP: {msg}")
                warnings.append(msg)
            else:
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

    import_failures = [f for f in failures if f.startswith("import app.main:")]
    if import_failures and server_up and not args.strict_import:
        for f in import_failures:
            failures.remove(f)
            warnings.append(f"{f} (ignored because running API is healthy; use --strict-import to fail)")
            print(f"WARN: {f} ignored because API is healthy")

    print("\n== Summary ==")
    metrics = monitor.summary() if monitor else {}
    if metrics:
        print("metrics:", json.dumps(metrics, indent=2))
    json_path = Path(str(args.log_file).replace(".log", ".json"))
    json_path.write_text(json.dumps({"failures": failures, "warnings": warnings, "failure_count": len(failures), "metrics": metrics}, indent=2), encoding="utf-8")
    if warnings:
        print("WARNINGS:")
        for item in warnings:
            print(f"- {item}")
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
    p = argparse.ArgumentParser(description="SyMoNeuRaL_ML smoke test with automatic logs and CPU/VRAM metrics")
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--log-file")
    p.add_argument("--no-api", action="store_true")
    p.add_argument("--no-job", action="store_true")
    p.add_argument("--require-server", action="store_true")
    p.add_argument("--strict-import", action="store_true")
    p.add_argument("--no-metrics", action="store_true")
    p.add_argument("--metrics-interval", type=float, default=1.0)
    args = p.parse_args()
    path = log_path("test", args.log_file)
    args.log_file = str(path)
    monitor = None if args.no_metrics else ResourceMonitor("test", args.metrics_interval)
    tee = Tee(path)
    with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
        try:
            if monitor:
                monitor.start()
            code = run(args, monitor)
        finally:
            if monitor:
                monitor.stop()
            print(f"\nLOG_FILE={path}")
            if monitor:
                print(f"METRICS_CSV={monitor.csv_path}")
                print(f"METRICS_SUMMARY={monitor.summary_path}")
            tee.flush()
    tee.close()
    print(f"Saved test log: {path}")
    if monitor:
        print(f"Saved metrics CSV: {monitor.csv_path}")
        print(f"Saved metrics summary: {monitor.summary_path}")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
