# RTX 5070 Ti Permanent 14-15GB VRAM Profile

This project is tuned for the user's NVIDIA GeForce RTX 5070 Ti 16GB card.

Do not revert SyMoNeuRaL startup back to the old conservative ~8GB llama-server profile.

Permanent target:

- llama.cpp GPU layers: 999
- writer context: 65536
- writer batch: 4096
- writer ubatch: 512
- writer parallel: 1
- code context: 65536
- code batch: 4096
- code ubatch: 512
- code parallel: 1
- image default: 1152x1152, 40 steps
- target total GPU memory: 14000-15360 MiB

Canonical config:

- `config/rtx5070ti_14_15gb.env`
- `scripts/symon_env_5070ti_max.sh`
- `scripts/symon`

Canonical startup command:

```bash
./scripts/symon
```

Reason:

The RTX 5070 Ti has 16GB VRAM. Conservative 8GB profiles waste the card and have repeatedly caused confusion. All launchers should source `scripts/symon_env_5070ti_max.sh` so every normal start uses the 14-15GB profile unless the user explicitly overrides it for debugging.
