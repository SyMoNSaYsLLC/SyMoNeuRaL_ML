from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class VramProcess:
    pid: str
    used_mib: str
    name: str


def nvidia_smi_snapshot() -> dict:
    base = {"ok": False, "summary": None, "processes": [], "error": None}
    try:
        summary = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=3,
        )
        if summary.stdout.strip():
            vals = [x.strip() for x in summary.stdout.splitlines()[0].split(",")]
            if len(vals) >= 6:
                base["summary"] = {
                    "gpu_name": vals[0], "memory_used_mib": vals[1], "memory_total_mib": vals[2],
                    "utilization_percent": vals[3], "power_w": vals[4], "temperature_c": vals[5],
                }
        proc = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory,process_name", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=3,
        )
        rows = []
        for line in proc.stdout.splitlines():
            parts = [x.strip() for x in line.split(",", 2)]
            if len(parts) == 3:
                rows.append({"pid": parts[0], "used_mib": parts[1], "process_name": parts[2]})
        base.update({"ok": True, "processes": rows})
    except Exception as exc:
        base["error"] = repr(exc)
    return base
