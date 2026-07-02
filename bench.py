#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _venv_python() -> Path | None:
    # Try the common venv launchers in order. Some Python installs create python3 only.
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
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

TERMINAL = {"done", "failed", "needs-review"}

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
        (ROOT / "logs").mkdir(exist_ok=True)
        p = ROOT / "logs" / f"{prefix}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 240) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        return json.loads(body) if body else {}

def nvidia_smi() -> str:
    try:
        return subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits",
        ], text=True, stderr=subprocess.STDOUT, timeout=8).strip()
    except Exception as exc:
        return f"nvidia-smi unavailable: {exc!r}"

def header(name: str) -> None:
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

def wait_job(base: str, job_id: str, poll: float, timeout: float) -> dict[str, Any]:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        job = http_json("GET", f"{base}/api/v1/manager/jobs/{job_id}?include_image=false", timeout=30)
        status = job.get("status", "unknown")
        if status != last:
            print(f"job {job_id}: {status}")
            last = status
        if status in TERMINAL:
            return job
        time.sleep(poll)
    raise TimeoutError(f"job {job_id} timed out after {timeout}s")

def run_job(base: str, name: str, payload: dict[str, Any], poll: float, timeout: float) -> dict[str, Any]:
    header(name)
    print("VRAM before:", nvidia_smi())
    started = time.time()
    result: dict[str, Any] = {"name": name, "ok": False}
    try:
        job = http_json("POST", f"{base}/api/v1/manager/submit", payload, timeout=60)
        job_id = job.get("id")
        if not job_id:
            raise RuntimeError(f"No job id returned: {job}")
        print("submitted:", job_id)
        final = wait_job(base, job_id, poll, timeout)
        result.update({
            "ok": final.get("status") == "done",
            "seconds": time.time() - started,
            "status": final.get("status"),
            "job_id": job_id,
            "artifact_url": f"{base}/api/v1/manager/jobs/{job_id}/artifact" if final.get("artifact") or final.get("image_path") else None,
            "detail": final.get("result_text") or final.get("error") or final.get("user_message") or "",
        })
        print("VRAM after:", nvidia_smi())
        print("result:", result["status"])
        if result["artifact_url"]:
            print("artifact:", result["artifact_url"])
        if result["detail"]:
            print("detail:", str(result["detail"])[:1600])
    except Exception as exc:
        result.update({"seconds": time.time() - started, "status": "failed", "detail": repr(exc)})
        print("FAILED:", repr(exc))
        print("VRAM after:", nvidia_smi())
    return result

def run(args: argparse.Namespace) -> int:
    base = args.base.rstrip("/")
    results = []
    header("SyMoNeuRaL_ML Benchmark")
    print("started:", dt.datetime.now().isoformat(timespec="seconds"))
    print("root:", ROOT)
    print("python:", sys.executable)
    print("base:", base)
    print("log:", args.log_file)

    header("Health")
    try:
        health = http_json("GET", f"{base}/api/v1/health", timeout=30)
        print(json.dumps(health, indent=2)[:6000])
    except urllib.error.URLError as exc:
        print(f"SERVER_NOT_REACHABLE: {exc!r}")
        print("Start the server in another terminal:")
        print("  ./scripts/start_exclusive_16gb.sh")
        json_path = Path(str(args.log_file).replace(".log", ".json"))
        json_path.write_text(json.dumps({"failures": 1, "error": "server_not_reachable", "detail": repr(exc)}, indent=2), encoding="utf-8")
        print("json_summary:", json_path)
        return 1
    print("VRAM:", nvidia_smi())

    if not args.skip_writer:
        results.append(run_job(base, "Writer Manager", {"route": "writer", "prompt": args.writer_prompt}, args.poll, args.timeout))
    if not args.skip_code:
        results.append(run_job(base, "Code Handoff", {"route": "code", "prompt": args.code_prompt}, args.poll, args.timeout))
    if not args.skip_image:
        results.append(run_job(base, "Image Handoff", {
            "route": "image", "prompt": args.image_prompt,
            "width": args.image_width, "height": args.image_height,
            "steps": args.image_steps, "cfg_scale": 7.5, "seed": -1, "style": "cinematic",
        }, args.poll, args.timeout))

    header("Benchmark Summary")
    for r in results:
        print(f"{'OK' if r.get('ok') else 'FAIL'} | {r.get('name')} | {r.get('seconds', 0):.2f}s | {r.get('status')} | {r.get('job_id', '-')}")
        if r.get("artifact_url"):
            print("artifact:", r["artifact_url"])
    failures = sum(1 for r in results if not r.get("ok"))
    json_path = Path(str(args.log_file).replace(".log", ".json"))
    json_path.write_text(json.dumps({"results": results, "failures": failures}, indent=2), encoding="utf-8")
    print("json_summary:", json_path)
    print("finished:", dt.datetime.now().isoformat(timespec="seconds"))
    return 1 if failures else 0

def main() -> int:
    p = argparse.ArgumentParser(description="SyMoNeuRaL_ML benchmark; creates logs automatically")
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--poll", type=float, default=2.0)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--log-file")
    p.add_argument("--skip-writer", action="store_true")
    p.add_argument("--skip-code", action="store_true")
    p.add_argument("--skip-image", action="store_true")
    p.add_argument("--writer-prompt", default="Rewrite this professionally: the server works now and I need the build checked.")
    p.add_argument("--code-prompt", default="Make a simple Python hello-world CLI project and package it as a compressed artifact.")
    p.add_argument("--image-prompt", default="Generate a 512x512 cinematic image of a futuristic local AI server glowing in a dark workshop.")
    p.add_argument("--image-steps", type=int, default=24)
    p.add_argument("--image-width", type=int, default=512)
    p.add_argument("--image-height", type=int, default=512)
    args = p.parse_args()
    path = log_path("bench", args.log_file)
    args.log_file = str(path)
    tee = Tee(path)
    with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
        try:
            code = run(args)
        finally:
            print(f"\nLOG_FILE={path}")
            tee.flush()
    tee.close()
    print(f"Saved benchmark log: {path}")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
