# SyMoNeuRaL Local AI v9.1 Canonical Notes

This update keeps the v9 UI and adds a cleaner API/helper layer based on the new source repos:

- `Simple_API_Example-main.zip`: canonical minimal FastAPI server/client flow: simple endpoints, direct params, clear browser testing via `/docs`.
- `fine_tuning-main.zip`: canonical fine-tune planning shape: prompt/completion examples, LoRA/PEFT workflow, dataset validation before training.
- `rag_ollama-main.zip`: canonical helper idea: keep tuning knobs and retrieval/debug steps visible instead of hiding them.
- `APIREV 2.zip`: canonical larger API structure: health, services, scripts, database-style future expansion, performance metrics.

v9.1 does not try to train inside your running webserver yet. It adds safe planning endpoints and frontend helper chips so the UI becomes a workbench instead of a blank textarea.

## New endpoints

- `GET /api/v1/catalog` — lists engines, helper tools, and source inspirations.
- `POST /api/v1/generate` — unified API wrapper around writer/code/image.
- `POST /api/v1/tools/fine-tune-plan` — validates prompt/completion examples and returns a LoRA/PEFT plan.
- `GET /api/v1/tools/vram` — returns `nvidia-smi` process memory data when available.

## VRAM idea

Use llama.cpp server knobs first:

- `--gpu-layers` / `-ngl` for VRAM residency
- `-c` for context size
- `-np` for slots
- `-b` and `-ub` for batch/ubatch
- optional KV cache quantization if your binary supports it

Then watch live memory with `scripts/vram_watch.sh` or the `/api/v1/tools/vram` endpoint.
