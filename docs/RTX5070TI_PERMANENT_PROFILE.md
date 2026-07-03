# RTX 5070 Ti Permanent 14-15GB VRAM Profile

This repo is tuned for the user's NVIDIA GeForce RTX 5070 Ti 16GB card.

Canonical startup:

```bash
./scripts/symon
```

Do not use old launcher names as source-of-truth. They are compatibility wrappers.

Permanent target:

- Total GPU memory: 14000-15360 MiB, including KDE/desktop
- Writer process should appear as `bin/symon-llm-server`, not the upstream `llama-server`
- llama.cpp GPU layers: 999
- writer context: 294912
- writer parallel: 2
- writer batch: 4096
- writer ubatch: 512
- code context: 294912
- code parallel: 1
- image default: 1216x1216, 40 steps

Why this exists:

Adaptive routing previously lowered the writer/manager context back to 8192/16384 and restarted the server around an 8-9GB profile. That wastes the 5070 Ti and caused repeated regressions. The adaptive profile code now keeps the permanent context floor whenever `SYMON_FORCE_TEXT_MAX=1`.

Source of truth:

- `config/rtx5070ti_14_15gb.env`
- `scripts/symon`
- `app/services/process_manager.py`
- `app/services/symon_adaptive_profiles.py`
