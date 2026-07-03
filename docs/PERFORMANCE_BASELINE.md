# RTX 5070 Ti Performance Baseline

The 20:04 benchmark proved the system is stable after the first max profile:

```text
Writer Manager: ~2.01s
Code Handoff:   ~6.01s
Image Handoff:  ~10.02s
Failures:       0
```

The metrics CSV showed the GPU was active but still had headroom:

```text
Max VRAM used:  ~8908 MiB of 16303 MiB
Max GPU util:   97%
Max power draw: ~236 W of 300 W cap
Max temp:       ~66 C
```

## Current turbo target

The default 16GB launcher now runs the RTX 5070 Ti turbo profile:

```bash
./scripts/start_exclusive_16gb.sh
```

It maps to:

```bash
./scripts/start_exclusive_5070ti_turbo.sh
```

Turbo defaults:

```text
writer gpu layers: 999
writer context:    8192
writer batch:      1024
writer ubatch:     256

code gpu layers:   999
code context:      16384
code batch:        1024
code ubatch:       256

image default:     768x768
image steps:       32
```

Safe fallback:

```bash
./scripts/start_exclusive_16gb_safe.sh
```

Benchmark:

```bash
./scripts/bench_performance.sh
```
