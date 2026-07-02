# Shipping Ready Migration

## Canonical output

This tree is the canonical shipping form for `SyMoNeuRaL_Local_ML`. The active application code is not spread across the source archives. It lives in:

```text
app/
frontend/
helpers/
scripts/
deploy/
billing/
data/
```

The uploaded projects are preserved under `source_projects/` where useful for traceability.

## Runtime model

The production runtime uses exclusive VRAM handoff:

```text
Normal/easy prompt:
User -> Gemma Writer Manager -> User

Code prompt:
User -> Gemma Writer Manager -> stop Writer -> start Qwen Code Worker -> build/test/package -> stop Qwen -> restart Writer -> assess -> User

Image prompt:
User -> Gemma Writer Manager -> stop Writer -> start Stable Diffusion Worker -> render -> stop SD -> restart Writer -> assess -> User
```

This prevents Gemma + Qwen + SD from occupying VRAM at the same time.

## Shipping checks

Run:

```bash
./scripts/doctor.sh
./scripts/production_check.sh
./scripts/start_exclusive_16gb.sh
```

Then open:

```text
http://127.0.0.1:8000
```
