from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.core.billing import create_checkout_session, stripe_status
from app.core.cloudflare import tunnel_config, write_tunnel_config
from app.core.config import get_settings
from app.core.security import require_api_key
from app.core.vram import nvidia_smi_snapshot
from app.core.cuda_model_tools import cuda_toolchain_snapshot, model_inventory, run_build, hf_to_gguf_command
from app.services.background_coder import BACKGROUND_CODER
from app.services.exclusive_handoff import EXCLUSIVE_HANDOFF
from app.services.fine_tune import build_fine_tune_plan
from app.services.llama_cpp import build_chat_payload, stream_chat_completion
from app.services.moe_router import choose_expert
from app.services.sd_cpp import image_payload_attempts
from app.workers.job_manager import JOB_MANAGER

router = APIRouter(prefix="/api/v1", tags=["SyMoNeuRaL Local ML v1"], dependencies=[Depends(require_api_key)])


def engine_cfg(name: str) -> dict[str, Any]:
    settings = get_settings()
    cfg = settings.engines.get(name)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Engine {name} not configured")
    return cfg


@router.get("/catalog")
def catalog() -> dict:
    settings = get_settings()
    return {
        "name": settings.raw.get("app", {}).get("name", "SyMoNeuRaL Local ML"),
        "version": settings.raw.get("app", {}).get("version", "1.4.0-cuda-model-tools"),
        "orchestration": {
            "mode": "exclusive-vram-handoff",
            "resident_engine": settings.raw.get("orchestration", {}).get("resident_engine", "writer"),
            "description": "Only the Writer Manager stays resident. Code/Image workers receive the whole GPU during handoff, then shut down.",
        },
        "public_experts": [
            {"id": "writer", "label": "Gemma Writer Manager", "route": "/api/v1/manager/submit"},
            {"id": "image", "label": "Image handoff via Writer Manager", "route": "/api/v1/manager/submit"},
        ],
        "background_workers": [
            {"id": "code", "label": "Qwen Background Code Agent", "visible": False},
            {"id": "image", "label": "Stable Diffusion Worker", "visible": False},
        ],
        "handoff_routes": [
            "POST /api/v1/manager/submit",
            "GET /api/v1/manager/jobs",
            "GET /api/v1/manager/jobs/{job_id}",
            "GET /api/v1/manager/jobs/{job_id}/artifact",
        ],
        "legacy_routes": [
            "POST /api/v1/generate",
            "POST /api/v1/images/generations",
            "POST /api/v1/coder/background",
        ],
        "tools": ["/api/v1/tools/vram", "/api/v1/fine-tune/plan", "/api/v1/billing/status", "/api/v1/cloudflare/tunnel-config"],
    }


@router.get("/health")
def health(request: Request) -> dict:
    manager = request.app.state.engine_manager
    return {
        "ok": True,
        "engines": manager.status(),
        "vram": nvidia_smi_snapshot(),
        "handoff_jobs": EXCLUSIVE_HANDOFF.list()[:5],
        "coder_jobs": BACKGROUND_CODER.list()[:5],
    }


@router.post("/manager/submit")
async def manager_submit(data: dict, request: Request) -> dict:
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    route = data.get("route") or data.get("expert")
    if route not in {None, "writer", "code", "image"}:
        route = None
    job = EXCLUSIVE_HANDOFF.submit(
        prompt=prompt,
        app=request.app,
        requested_route=route,
        image_options=data,
    )
    return {
        **job.as_dict(),
        "message": "This task requires a lot of processing power, but please wait — your code/image is coming soon." if route in {"code", "image"} else "Writer Manager is processing.",
    }


@router.get("/manager/jobs")
def manager_jobs() -> dict:
    return {"jobs": EXCLUSIVE_HANDOFF.list()}


@router.get("/manager/jobs/{job_id}")
def manager_job(job_id: str, include_image: bool = True) -> dict:
    try:
        return EXCLUSIVE_HANDOFF.get(job_id, include_image=include_image)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="handoff job not found") from exc


@router.get("/manager/jobs/{job_id}/artifact")
def manager_artifact(job_id: str):
    try:
        path = EXCLUSIVE_HANDOFF.artifact_path(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="handoff job not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact not ready") from exc
    media = "image/png" if Path(path).suffix.lower() == ".png" else "application/gzip"
    return FileResponse(path, filename=Path(path).name, media_type=media)


@router.post("/generate")
async def generate(data: dict, request: Request):
    """
    Backward-compatible route.
    In production exclusive mode, prefer /manager/submit so handoffs can free VRAM.
    """
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    expert = data.get("expert") or choose_expert(prompt)
    if data.get("handoff", True):
        job = EXCLUSIVE_HANDOFF.submit(prompt=prompt, app=request.app, requested_route=expert if expert in {"writer", "code", "image"} else None, image_options=data)
        return job.as_dict()

    cfg = engine_cfg("writer")
    request.app.state.engine_manager.switch_exclusive_sync("writer")
    defaults = cfg.get("defaults", {})
    system = data.get("system_prompt") or "You are SyMoNeuRaL Gemma Writer Manager. Answer directly or create a clean implementation-ready handoff request."
    payload = build_chat_payload(
        prompt=prompt,
        system_prompt=system,
        temperature=float(data.get("temperature", defaults.get("temperature", 0.65))),
        top_p=float(data.get("top_p", defaults.get("top_p", 0.95))),
        max_tokens=int(data.get("max_tokens", defaults.get("max_tokens", 900))),
        stream=bool(data.get("stream", True)),
    )
    if payload["stream"]:
        return StreamingResponse(stream_chat_completion(cfg["endpoint"], payload), media_type="text/event-stream")
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(cfg["endpoint"], json=payload)
        return JSONResponse(resp.json(), status_code=resp.status_code)


@router.post("/chat/completions")
async def openai_chat_completions(data: dict, request: Request):
    # OpenAI-compatible visible chat always routes to the writer/manager.
    cfg = engine_cfg("writer")
    request.app.state.engine_manager.switch_exclusive_sync("writer")
    data = {**data, "stream": data.get("stream", True)}
    if data["stream"]:
        return StreamingResponse(stream_chat_completion(cfg["endpoint"], data), media_type="text/event-stream")
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(cfg["endpoint"], json=data)
        return JSONResponse(resp.json(), status_code=resp.status_code)


@router.post("/images/generations")
async def images_generations(data: dict, request: Request):
    # Compatibility route. It now runs image exclusively, then restores the writer.
    cfg = engine_cfg("image")
    request.app.state.engine_manager.switch_exclusive_sync("image")
    errors = []
    try:
        async with httpx.AsyncClient(timeout=240) as client:
            for label, payload in image_payload_attempts(data):
                resp = await client.post(cfg["endpoint"], json=payload)
                if resp.status_code < 400:
                    try:
                        parsed = resp.json()
                    except Exception:
                        return JSONResponse({"raw": resp.text, "payload_mode": label})
                    if parsed.get("images"):
                        parsed["payload_mode"] = label
                        return parsed
                    errors.append({"mode": label, "status": resp.status_code, "body": resp.text[:800]})
                else:
                    errors.append({"mode": label, "status": resp.status_code, "body": resp.text[:800]})
        return JSONResponse({"error": "image generation failed", "attempts": errors}, status_code=502)
    finally:
        request.app.state.engine_manager.restart_resident_sync()


@router.post("/coder/background")
def coder_background(data: dict, request: Request) -> dict:
    """
    Legacy hidden Qwen coder route.
    For max VRAM, new production uses /manager/submit. This route still switches exclusively to code.
    """
    prompt = (data.get("prompt") or "").strip()
    writer_response = (data.get("writer_response") or data.get("writer_plan") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt required")
    request.app.state.engine_manager.switch_exclusive_sync("code")
    code_cfg = engine_cfg("code")
    job = BACKGROUND_CODER.submit(prompt=prompt, writer_response=writer_response, code_endpoint=code_cfg["endpoint"])
    return job.as_dict()


@router.get("/coder/jobs")
def coder_jobs() -> dict:
    return {"jobs": BACKGROUND_CODER.list()}


@router.get("/coder/jobs/{job_id}")
def coder_job(job_id: str) -> dict:
    try:
        return BACKGROUND_CODER.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="coder job not found") from exc


@router.get("/coder/jobs/{job_id}/artifact")
def coder_artifact(job_id: str):
    try:
        path = BACKGROUND_CODER.artifact_path(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="coder job not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact not ready") from exc
    return FileResponse(path, filename=Path(path).name, media_type="application/gzip")


@router.get("/tools/vram")
def tools_vram() -> dict:
    return nvidia_smi_snapshot()




@router.get("/tools/cuda")
def tools_cuda() -> dict:
    """CUDA/build toolchain snapshot: nvidia-smi, nvcc, cmake, Python, engine binary discovery."""
    settings = get_settings()
    return cuda_toolchain_snapshot(settings.root)


@router.get("/tools/models")
def tools_models() -> dict:
    """Inventory GGUF, safetensors, adapters, and other local model files."""
    settings = get_settings()
    return model_inventory(settings.root)


@router.post("/tools/build")
def tools_build(data: dict) -> dict:
    """
    Build llama.cpp, stable-diffusion.cpp, or both with CUDA through the project build scripts.
    Body: {"target": "all|llama|sd", "clean": false}
    """
    settings = get_settings()
    target = data.get("target", "all")
    clean = bool(data.get("clean", False))
    job = JOB_MANAGER.submit(f"build-{target}", data, lambda payload: run_build(settings.root, payload.get("target", "all"), clean=bool(payload.get("clean", False))))
    return job.__dict__


@router.post("/tools/convert/hf-to-gguf")
def tools_hf_to_gguf(data: dict) -> dict:
    """
    Return the exact convert command for llama.cpp's convert_hf_to_gguf.py.
    Set {"run": true} to run it as a background job.
    """
    settings = get_settings()
    model_dir = data.get("model_dir")
    if not model_dir:
        raise HTTPException(status_code=400, detail="model_dir required")
    outfile = data.get("outfile")
    outtype = data.get("outtype", "f16")
    try:
        cmd = hf_to_gguf_command(settings.root, model_dir, outfile=outfile, outtype=outtype)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if data.get("run"):
        def _run(payload: dict):
            import subprocess
            p = subprocess.run(cmd, cwd=settings.root, text=True, capture_output=True, timeout=7200)
            return {"ok": p.returncode == 0, "cmd": cmd, "returncode": p.returncode, "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:]}
        job = JOB_MANAGER.submit("hf-to-gguf", data, _run)
        return {"cmd": cmd, "job": job.__dict__}
    return {"cmd": cmd, "run": False}


@router.post("/fine-tune/plan")
def fine_tune_plan(data: dict) -> dict:
    return build_fine_tune_plan(data)


@router.post("/fine-tune/jobs")
def fine_tune_job(data: dict) -> dict:
    job = JOB_MANAGER.submit("fine-tune-plan", data, build_fine_tune_plan)
    return job.__dict__


@router.get("/jobs")
def list_jobs() -> dict:
    return {"jobs": JOB_MANAGER.list(), "coder_jobs": BACKGROUND_CODER.list(), "handoff_jobs": EXCLUSIVE_HANDOFF.list()}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    try:
        return JOB_MANAGER.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


@router.get("/billing/status")
def billing_status() -> dict:
    return stripe_status()


@router.post("/billing/checkout")
def billing_checkout(data: dict) -> dict:
    return create_checkout_session(data.get("success_url", "http://localhost:8000/?paid=1"), data.get("cancel_url", "http://localhost:8000/?paid=0"))


@router.get("/cloudflare/tunnel-config")
def cloudflare_config(hostname: str | None = None) -> dict:
    return {"config_yaml": tunnel_config(hostname=hostname)}


@router.post("/cloudflare/write-config")
def cloudflare_write(data: dict) -> dict:
    return write_tunnel_config(data.get("path", "deploy/cloudflare/config.yml"), data.get("hostname"))
