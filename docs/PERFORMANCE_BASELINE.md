# RTX 5070 Ti 14GB VRAM Target Profile

The previous turbo profile passed but only peaked around 9 GiB total GPU memory. The current target is to push benchmark peak GPU memory above 14,000 MiB while retaining exclusive handoff stability.

## Default launcher

```bash
./scripts/start_exclusive_16gb.sh
```

This maps to:

```bash
./scripts/start_exclusive_5070ti_vram14k.sh
```

## 14GB target defaults

```text
writer gpu layers: 999
writer context:    16384
writer batch:      2048
writer ubatch:     512

code gpu layers:   999
code context:      32768
code batch:        2048
code ubatch:       512

image default:     1024x1024
image steps:       36
target peak VRAM:  >= 14000 MiB
```

## Benchmark

```bash
./scripts/bench_vram14k.sh
```

or:

```bash
./scripts/bench_performance.sh
```

## If still under 14GB

Run an image-only stress pass:

```bash
SYMON_BENCH_IMAGE_WIDTH=1152 SYMON_BENCH_IMAGE_HEIGHT=1152 SYMON_BENCH_IMAGE_STEPS=40 python bench.py --skip-writer --skip-code
```

## Fallbacks

Previous turbo launcher:

```bash
./scripts/start_exclusive_16gb_turbo.sh
```

Safe launcher, if present:

```bash
./scripts/start_exclusive_16gb_safe.sh
```
