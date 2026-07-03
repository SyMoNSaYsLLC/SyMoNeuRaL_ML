# SyMoNeuRaL Adaptive Task Profiles

This update applies prompt-driven profile selection across:

```text
writer/chat/manager/helper
code/coding/helper/manager
image/text-to-image/image worker/manager
```

The Writer Manager chooses a route, then the runtime profile adjusts the active worker settings before handoff.

## Writer / chat / manager

```text
fast:
  quick, short, one-sentence, simple rewrites

balanced:
  normal chat, normal writing, normal explanations

deep / longform:
  architecture, production, debug, OpenEmbedded, detailed reports
```

## Code / coding helper

```text
fast-code:
  scripts, small patches, hello-world, bench.py/test.py

balanced-code:
  normal implementation tasks

repo-heavy:
  full repo, production, shipping, CUDA, CMake, OpenEmbedded, BitBake, major backend
```

## Image / text-to-image

```text
fast:
  768x768 / 24 steps
  quick, preview, draft, simple

balanced:
  1024x1024 / 30 steps
  default

quality:
  1024x1024 / 36 steps
  cinematic, professional, photorealistic, high detail

max:
  1152x1152 / 40 steps
  final, production, print, best quality

stress:
  1216x1216 / 40 steps
  benchmark, max VRAM, 14GB, use all VRAM
```

Explicit prompt dimensions like `1024x1024` are honored within the safety cap.

## Probe profiles

```bash
python scripts/profile_probe.py --route image "quick preview of a robot"
python scripts/profile_probe.py --route image "professional cinematic high detail server room"
python scripts/profile_probe.py --route code "major backend CUDA CMake repo update"
python scripts/profile_probe.py --route writer --phase manager "debug this architecture"
```
