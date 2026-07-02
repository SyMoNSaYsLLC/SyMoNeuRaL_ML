# Bench and Test Scripts

The scripts create all logs automatically. Do not wrap them with `tee`.

They auto-run through `.venv/bin/python` or `.venv/bin/python3` when available.

## Smoke test

```bash
python test.py
```

Creates:

```text
logs/test_YYYYMMDD_HHMMSS.log
logs/test_YYYYMMDD_HHMMSS.json
logs/test_YYYYMMDD_HHMMSS_metrics.csv
logs/test_YYYYMMDD_HHMMSS_metrics_summary.json
```

## Benchmark

```bash
python bench.py
```

Creates:

```text
logs/bench_YYYYMMDD_HHMMSS.log
logs/bench_YYYYMMDD_HHMMSS.json
logs/bench_YYYYMMDD_HHMMSS_metrics.csv
logs/bench_YYYYMMDD_HHMMSS_metrics_summary.json
```

## Metrics collected

- CPU percent
- 1/5/15 minute load average
- RAM used and total
- GPU VRAM used and total
- GPU utilization
- GPU power draw
- GPU temperature
- active NVIDIA compute processes
- top CPU processes

## Useful commands

```bash
python test.py --no-api
python test.py --no-job
python bench.py --skip-code --skip-image
python bench.py --skip-writer --skip-image
python bench.py --skip-writer --skip-code
python bench.py --no-metrics
python resource_monitor.py --out logs/manual_metrics.csv --duration 60
```
