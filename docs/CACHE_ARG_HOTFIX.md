# Cache Argument + VRAM Guard Hotfix

This fixes the llama.cpp startup failure:

`error while handling argument "--cache-type-v": expected value for argument`

Cause: old extra-arg handling appended tokens one at a time and skipped duplicate values. Since `f16` appeared once for `--cache-type-k`, the second `f16` for `--cache-type-v` could be skipped.

Fix:

- cache type is now handled as first-class flags
- stale `--cache-type-k` / `--cache-type-v` args are stripped before replacement
- canonical cache vars live in `config/rtx5070ti_14_15gb.env`
- canonical startup remains `./scripts/symon`
