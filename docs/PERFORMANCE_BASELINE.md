# Performance Baseline and RTX 5070 Ti Profile

The initial conservative run proved the full three-model system works:

- Writer Manager: about 20 seconds
- Code Handoff: about 16 seconds
- Image Handoff: about 20 seconds
- Failures: 0

The resource logs showed the RTX 5070 Ti was not close to full VRAM pressure. The writer process was around 3.2 GiB, and total GPU memory commonly sat around 4.3 GiB out of 16.3 GiB.

## Applied max profile

`scripts/start_exclusive_16gb.sh` now calls:

```bash
scripts/start_exclusive_5070ti_max.sh
```

The previous script is preserved as:

```bash
scripts/start_exclusive_16gb_safe.sh
```

## Max profile defaults

```text
writer gpu layers: 999
writer context:    4096
writer batch:      1024
writer ubatch:     256

code gpu layers:   999
code context:      8192
code batch:        1024
code ubatch:       256

image size:        512x512
image steps:       28
```

## Benchmark

```bash
./scripts/bench_performance.sh
```

This writes normal bench/test logs plus CPU/VRAM metrics logs.
