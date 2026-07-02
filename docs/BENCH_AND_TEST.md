# Bench and Test Scripts

The scripts create log files automatically. Do not wrap them with `tee`.

They also auto-run through `.venv/bin/python` when `.venv` exists, so normal usage is:

```bash
python test.py
python bench.py
```

## Smoke test

Local checks only, no server required:

```bash
python test.py --no-api
```

With the server running:

```bash
python test.py
```

The script writes:

```text
logs/test_YYYYMMDD_HHMMSS.log
logs/test_YYYYMMDD_HHMMSS.json
```

If the server is not running, `python test.py` will still complete local checks and mark API checks as skipped warnings unless `--require-server` is used.

## Benchmark

With the server running:

```bash
python bench.py
```

The script writes:

```text
logs/bench_YYYYMMDD_HHMMSS.log
logs/bench_YYYYMMDD_HHMMSS.json
```

Useful options:

```bash
python test.py --no-api
python test.py --no-job
python test.py --require-server
python bench.py --skip-code --skip-image
python bench.py --skip-writer --skip-image
python bench.py --skip-writer --skip-code
python bench.py --base http://192.168.1.50:8000
python test.py --log-file logs/my_test.log
python bench.py --log-file logs/my_bench.log
```
