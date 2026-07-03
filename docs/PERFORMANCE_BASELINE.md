# RTX 5070 Ti 14GB+ VRAM Target Profile

The 1024x1024 / 36-step pass completed with zero failures but peaked below the 14GB target. The next default profile is 1152x1152 / 40 steps.

## Default launcher

```bash
./scripts/start_exclusive_16gb.sh
```

This maps to:

```bash
./scripts/start_exclusive_5070ti_vram14k.sh
```

## 14GB+ target defaults

```text
writer gpu layers: 999
writer context:    16384
writer batch:      2048 target
writer ubatch:     512 target

code gpu layers:   999
code context:      32768
code batch:        2048 target
code ubatch:       512 target

image default:     1152x1152
image steps:       40
target peak VRAM:  >= 14000 MiB
```

Note: if backend logs still show `-b 512 -ub 128`, that only means the current process manager has hardcoded batch defaults. Context and image size are the larger VRAM drivers for the current benchmark.

## Full benchmark

```bash
./scripts/bench_vram14k.sh
```

## Image-only stress benchmark

```bash
./scripts/bench_image_vram.sh
```

If 1152x1152 is still below target:

```bash
SYMON_BENCH_IMAGE_WIDTH=1216 SYMON_BENCH_IMAGE_HEIGHT=1216 SYMON_BENCH_IMAGE_STEPS=40 ./scripts/bench_image_vram.sh
```

If OOM occurs:

```bash
SYMON_BENCH_IMAGE_WIDTH=1024 SYMON_BENCH_IMAGE_HEIGHT=1024 SYMON_BENCH_IMAGE_STEPS=36 ./scripts/bench_image_vram.sh
```
