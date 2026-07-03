#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
import json
from pathlib import Path
from statistics import mean


def latest(pattern: str) -> Path | None:
    files = sorted((Path(p) for p in glob.glob(pattern)), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"min": 0.0, "max": 0.0, "avg": 0.0}
    return {"min": round(min(vals), 2), "max": round(max(vals), 2), "avg": round(mean(vals), 2)}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    metrics = latest("logs/bench_*_metrics.csv") or latest("logs/test_*_metrics.csv")
    bench = latest("logs/bench_*.json")
    test = latest("logs/test_*.json")

    print("== SyMoNeuRaL performance report ==")
    if test:
        data = json.loads(test.read_text())
        print(f"test_json: {test}")
        print(f"test_failures: {data.get('failure_count', data.get('failures'))}")
    if bench:
        data = json.loads(bench.read_text())
        print(f"bench_json: {bench}")
        print(f"bench_failures: {data.get('failures')}")
        for r in data.get("results", []):
            print(f"  {r.get('name')}: {r.get('status')} {r.get('seconds', 0):.2f}s")

    if not metrics:
        print("No metrics CSV found.")
        return 0

    rows = read_csv(metrics)
    print(f"metrics_csv: {metrics}")
    print(f"samples: {len(rows)}")

    def nums(key: str) -> list[float]:
        out = []
        for r in rows:
            try:
                out.append(float(r.get(key, "0") or 0))
            except ValueError:
                pass
        return out

    for key in [
        "cpu_percent",
        "load_1m",
        "ram_used_mib",
        "gpu_memory_used_mib",
        "gpu_util_percent",
        "gpu_power_w",
        "gpu_temp_c",
    ]:
        print(f"{key}: {stats(nums(key))}")

    total = nums("gpu_memory_total_mib")
    used = nums("gpu_memory_used_mib")
    if total and used:
        print(f"max_vram_percent: {round(max(used) / max(total) * 100, 2)}%")

    print()
    print("Interpretation:")
    print("- If max_vram_percent is under 60% on a 16GB GPU, the server is conservative.")
    print("- For exclusive handoff mode, push layers/context/batch higher because only one worker owns the GPU at a time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
