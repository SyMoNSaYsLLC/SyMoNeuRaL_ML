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
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def read_loadavg() -> tuple[float, float, float]:
    try:
        a, b, c, *_ = Path("/proc/loadavg").read_text().split()
        return float(a), float(b), float(c)
    except Exception:
        return 0.0, 0.0, 0.0


def read_meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, val = line.split(":", 1)
            parts = val.strip().split()
            if parts:
                out[key] = int(parts[0])
    except Exception:
        pass
    return out


def cpu_snapshot() -> tuple[int, int]:
    try:
        parts = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals)
        return total, idle
    except Exception:
        return 0, 0


def gpu_snapshot() -> dict[str, Any]:
    try:
        raw = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=8,
        ).strip()
        name, mem_used, mem_total, util, power, temp = [x.strip() for x in raw.split(",", 5)]
        return {
            "gpu_name": name,
            "gpu_memory_used_mib": float(mem_used),
            "gpu_memory_total_mib": float(mem_total),
            "gpu_util_percent": float(util),
            "gpu_power_w": float(power),
            "gpu_temp_c": float(temp),
        }
    except Exception as exc:
        return {
            "gpu_name": "unavailable",
            "gpu_memory_used_mib": 0.0,
            "gpu_memory_total_mib": 0.0,
            "gpu_util_percent": 0.0,
            "gpu_power_w": 0.0,
            "gpu_temp_c": 0.0,
            "gpu_error": repr(exc),
        }


def gpu_processes() -> str:
    try:
        return subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,process_name,used_memory",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=8,
        ).strip().replace("\n", " | ")
    except Exception:
        return ""


def top_cpu_processes(limit: int = 8) -> str:
    try:
        out = subprocess.check_output(
            ["bash", "-lc", f"ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n {limit + 1}"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        return " | ".join(line.strip() for line in out.splitlines()[1:] if line.strip())
    except Exception:
        return ""


def summarize_csv(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {"samples": 0}

    def nums(key: str) -> list[float]:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(key, "0") or 0))
            except Exception:
                pass
        return vals

    def stat(key: str) -> dict[str, float]:
        vals = nums(key)
        if not vals:
            return {"min": 0, "max": 0, "avg": 0}
        return {"min": min(vals), "max": max(vals), "avg": sum(vals) / len(vals)}

    return {
        "samples": len(rows),
        "first_timestamp": rows[0].get("timestamp"),
        "last_timestamp": rows[-1].get("timestamp"),
        "cpu_percent": stat("cpu_percent"),
        "load_1m": stat("load_1m"),
        "ram_used_mib": stat("ram_used_mib"),
        "gpu_memory_used_mib": stat("gpu_memory_used_mib"),
        "gpu_util_percent": stat("gpu_util_percent"),
        "gpu_power_w": stat("gpu_power_w"),
        "gpu_temp_c": stat("gpu_temp_c"),
    }


def write_sample(writer: csv.DictWriter, previous_cpu: tuple[int, int] | None) -> tuple[int, int]:
    now = dt.datetime.now().isoformat(timespec="seconds")
    total, idle = cpu_snapshot()
    if previous_cpu and total > previous_cpu[0]:
        delta_total = total - previous_cpu[0]
        delta_idle = idle - previous_cpu[1]
        cpu_percent = max(0.0, min(100.0, 100.0 * (1.0 - (delta_idle / delta_total))))
    else:
        cpu_percent = 0.0

    load_1m, load_5m, load_15m = read_loadavg()
    mem = read_meminfo()
    mem_total = mem.get("MemTotal", 0) / 1024
    mem_avail = mem.get("MemAvailable", 0) / 1024
    mem_used = max(0.0, mem_total - mem_avail)

    gpu = gpu_snapshot()
    row = {
        "timestamp": now,
        "cpu_percent": round(cpu_percent, 2),
        "load_1m": load_1m,
        "load_5m": load_5m,
        "load_15m": load_15m,
        "ram_used_mib": round(mem_used, 1),
        "ram_total_mib": round(mem_total, 1),
        "gpu_name": gpu.get("gpu_name", ""),
        "gpu_memory_used_mib": gpu.get("gpu_memory_used_mib", 0),
        "gpu_memory_total_mib": gpu.get("gpu_memory_total_mib", 0),
        "gpu_util_percent": gpu.get("gpu_util_percent", 0),
        "gpu_power_w": gpu.get("gpu_power_w", 0),
        "gpu_temp_c": gpu.get("gpu_temp_c", 0),
        "gpu_processes": gpu_processes(),
        "top_cpu_processes": top_cpu_processes(),
    }
    writer.writerow(row)
    return total, idle


def main() -> int:
    p = argparse.ArgumentParser(description="SyMoNeuRaL_ML CPU/VRAM metrics logger")
    p.add_argument("--out", required=True, help="CSV output path")
    p.add_argument("--summary", default=None, help="JSON summary output path")
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--duration", type=float, default=0.0, help="0 means run until Ctrl+C")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = Path(args.summary) if args.summary else Path(str(out).replace(".csv", "_summary.json"))

    fields = [
        "timestamp",
        "cpu_percent",
        "load_1m",
        "load_5m",
        "load_15m",
        "ram_used_mib",
        "ram_total_mib",
        "gpu_name",
        "gpu_memory_used_mib",
        "gpu_memory_total_mib",
        "gpu_util_percent",
        "gpu_power_w",
        "gpu_temp_c",
        "gpu_processes",
        "top_cpu_processes",
    ]

    deadline = time.time() + args.duration if args.duration and args.duration > 0 else None
    previous_cpu = None

    with out.open("w", encoding="utf-8", newline="", buffering=1) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        try:
            while True:
                previous_cpu = write_sample(writer, previous_cpu)
                f.flush()
                if deadline and time.time() >= deadline:
                    break
                time.sleep(max(0.2, args.interval))
        except KeyboardInterrupt:
            pass

    summary.write_text(json.dumps(summarize_csv(out), indent=2), encoding="utf-8")
    print(f"METRICS_CSV={out}")
    print(f"METRICS_SUMMARY={summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
