import asyncio
import json
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from services.diff import DiffService
from services.gemma import GemmaService
from services.writer import WriterService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyMoNeuRaL")

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

services = {
    "chat": GemmaService(),
    "code": WriterService(),
    "img": DiffService(),
}
processes = {}


def _replace_flag(cmd, old_flags, new_flag):
    return [new_flag if item in old_flags else item for item in cmd]


def _has_any(cmd, flags):
    return any(part in flags for part in cmd)


def _set_or_append(cmd, flags, value):
    out = []
    replaced = False
    i = 0
    while i < len(cmd):
        item = cmd[i]
        if item in flags:
            out.extend([flags[0], str(value)])
            i += 2
            replaced = True
        else:
            out.append(item)
            i += 1
    if not replaced:
        out.extend([flags[0], str(value)])
    return out


def find_shared_library_dirs():
    dirs = set()
    for base in [
        ROOT / "engines" / "llama.cpp" / "build",
        ROOT / "engines" / "stable-diffusion.cpp" / "build",
    ]:
        if not base.exists():
            continue
        for path in base.rglob("*.so"):
            if path.is_file():
                dirs.add(str(path.parent.resolve()))
    return sorted(dirs)


def normalize_engine_cmd(name, cmd):
    cmd = list(cmd)
    binary = Path(cmd[0]).name
    if binary == "llama-server":
        cmd = _replace_flag(cmd, {"--ngl", "-ngl"}, "--gpu-layers")
        gpu_layers = os.getenv(f"SYMON_{name.upper()}_GPU_LAYERS")
        if gpu_layers:
            cmd = _set_or_append(cmd, ["--gpu-layers"], gpu_layers)
        if not _has_any(cmd, {"-c", "--ctx-size"}):
            ctx = os.getenv(f"SYMON_{name.upper()}_CTX", os.getenv("SYMON_DEFAULT_CTX", "4096"))
            cmd.extend(["-c", ctx])
        if not _has_any(cmd, {"-np", "--parallel"}):
            cmd.extend(["-np", os.getenv(f"SYMON_{name.upper()}_NP", "1")])
        if not _has_any(cmd, {"-b", "--batch-size"}):
            cmd.extend(["-b", os.getenv(f"SYMON_{name.upper()}_BATCH", "512")])
        if not _has_any(cmd, {"-ub", "--ubatch-size"}):
            cmd.extend(["-ub", os.getenv(f"SYMON_{name.upper()}_UBATCH", "128")])
    return cmd


async def probe_endpoint(url, timeout=0.75):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        return False


async def stream_upstream(url, payload):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                yield f"data: {json.dumps({'error': body.decode('utf-8', 'replace') or resp.reason_phrase})}\n\n".encode()
                return
            async for chunk in resp.aiter_bytes():
                yield chunk


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Spinning up SyMoNeuRaL engines...")
    env = os.environ.copy()

    lib_dirs = find_shared_library_dirs()
    if lib_dirs:
        current = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([current] if current else []))
        logger.info("LD_LIBRARY_PATH prepared with %d directories", len(lib_dirs))

    for name, cfg in config.get("engines", {}).items():
        cmd = normalize_engine_cmd(name, cfg["cmd"])
        logger.info("Starting %s: %s", name, " ".join(cmd))
        processes[name] = subprocess.Popen(cmd, cwd=str(ROOT), env=env, text=True)
        await asyncio.sleep(0.7)

    yield

    logger.info("Shutting down SyMoNeuRaL...")
    for name, p in processes.items():
        if p and p.poll() is None:
            logger.info("Stopping %s (pid %s)", name, p.pid)
            p.terminate()
    await asyncio.sleep(0.5)
    for p in processes.values():
        if p and p.poll() is None:
            p.kill()



SOURCE_CANON = {
    "Simple_API_Example": "minimal FastAPI server/client endpoints and browser testing through /docs",
    "fine_tuning": "prompt/completion dataset shape plus LoRA/PEFT planning before training",
    "rag_ollama": "visible hyperparameters, retrieval/debug workflow, and local model experimentation",
    "APIREV": "service-style API organization, health checks, scripts, metrics, and future database expansion",
}


def read_nvidia_smi():
    cmd = [
        "nvidia-smi",
        "--query-compute-apps=pid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=2.5)
        rows = []
        for line in proc.stdout.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 3:
                rows.append({"pid": parts[0], "process": parts[1], "used_mib": parts[2]})
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=2.5,
        )
        summary = None
        if gpu.stdout.strip():
            vals = [x.strip() for x in gpu.stdout.splitlines()[0].split(",")]
            if len(vals) >= 5:
                summary = {"memory_used_mib": vals[0], "memory_total_mib": vals[1], "gpu_util_percent": vals[2], "power_w": vals[3], "temperature_c": vals[4]}
        return {"ok": proc.returncode == 0, "summary": summary, "processes": rows, "stderr": proc.stderr.strip()}
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "processes": []}


def build_fine_tune_plan(data):
    examples = data.get("examples") or []
    model = data.get("base_model") or "qwen2.5-coder-1.5b-instruct"
    out = data.get("output_name") or "symon-lora-adapter"
    valid = []
    problems = []
    for i, ex in enumerate(examples):
        prompt = (ex.get("prompt") or "").strip() if isinstance(ex, dict) else ""
        completion = (ex.get("completion") or "").strip() if isinstance(ex, dict) else ""
        if not prompt or not completion:
            problems.append(f"example {i} needs prompt and completion")
        else:
            valid.append({"prompt": prompt, "completion": completion})
    return {
        "base_model": model,
        "output_name": out,
        "valid_examples": len(valid),
        "problems": problems,
        "recommended_min_examples": 50,
        "format": {"prompt": "user/task text", "completion": "ideal model answer"},
        "workflow": [
            "collect prompt/completion JSONL",
            "validate formatting and remove junk rows",
            "tokenize with the base model tokenizer",
            "train a LoRA/PEFT adapter, not a full model, for first pass",
            "test adapter outputs before merging or converting",
            "export adapter and record base model commit/path",
        ],
        "starter_command_notes": [
            "Use the fine_tuning repo notebook for the LoRA/PEFT notebook flow.",
            "Do not run fine-tuning inside the production FastAPI web server process.",
            "Keep training artifacts under models/adapters/<output_name>/.",
        ],
    }

app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health():
    report = {}
    for name, service in services.items():
        proc = processes.get(name)
        report[name] = {
            "pid": getattr(proc, "pid", None),
            "running": bool(proc and proc.poll() is None),
            "reachable": await probe_endpoint(service.get_health_endpoint()),
            "endpoint": service.get_api_endpoint(),
            "name": getattr(service, "name", name),
        }
    return report


@app.get("/api/config")
async def get_config():
    return {
        "tabs": ["chat", "code", "img"],
        "defaults": {
            "chat": {
                "temperature": 0.65,
                "top_p": 0.95,
                "max_tokens": 700,
                "system_prompt": "You are SyMoNeuRaL Gemma Writer. Write, rewrite, edit, summarize, and draft clean text. Be direct, useful, and do not add model chatter.",
            },
            "code": {
                "temperature": 0.2,
                "top_p": 0.95,
                "max_tokens": 1000,
                "system_prompt": "You are SyMoNeuRaL Code Writer powered by Qwen Coder. Return practical code, commands, paths, and concise explanations.",
            },
            "img": {
                "width": 512,
                "height": 512,
                "steps": 34,
                "cfg_scale": 7.5,
                "sampler_name": "Euler a",
                "seed": -1,
                "style": "cinematic",
                "enhance": True,
                "compat": False,
                "negative_prompt": "worst quality, low quality, normal quality, lowres, blurry, pixelated, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, malformed, deformed, duplicate, cropped, out of frame, watermark, text, logo, signature",
            },
        },
        "image_presets": {
            "fast": {"width": 512, "height": 512, "steps": 22, "cfg_scale": 7.0, "sampler_name": "Euler a"},
            "quality": {"width": 512, "height": 512, "steps": 34, "cfg_scale": 7.5, "sampler_name": "Euler a"},
            "landscape": {"width": 704, "height": 512, "steps": 34, "cfg_scale": 7.5, "sampler_name": "Euler a"},
            "portrait": {"width": 512, "height": 704, "steps": 34, "cfg_scale": 7.5, "sampler_name": "Euler a"},
        },
    }



@app.get("/api/v1/catalog")
async def api_catalog():
    return {
        "name": "SyMoNeuRaL Local AI API",
        "version": "9.1",
        "canonical_sources": SOURCE_CANON,
        "engines": {
            "chat": {"label": "Gemma Writer", "route": "/api/chat/generate", "unified": "/api/v1/generate"},
            "code": {"label": "Qwen Code", "route": "/api/code/generate", "unified": "/api/v1/generate"},
            "img": {"label": "Image Studio", "route": "/api/img/generate", "unified": "/api/v1/generate"},
        },
        "tools": {
            "vram": "/api/v1/tools/vram",
            "fine_tune_plan": "/api/v1/tools/fine-tune-plan",
            "openapi": "/docs",
        },
    }


@app.get("/api/v1/tools/vram")
async def api_vram():
    return read_nvidia_smi()


@app.post("/api/v1/tools/fine-tune-plan")
async def api_fine_tune_plan(request: Request):
    return build_fine_tune_plan(await request.json())


@app.post("/api/v1/generate")
async def api_v1_generate(request: Request):
    data = await request.json()
    engine = data.get("engine") or data.get("mode") or "chat"
    if engine == "writer":
        engine = "chat"
    if engine == "image":
        engine = "img"
    if engine not in services:
        raise HTTPException(status_code=404, detail=f"Unknown engine: {engine}")
    # Reuse the canonical local route logic by calling the same function with a tiny request shim.
    class Shim:
        async def json(self_inner):
            return data
    return await proxy_request(engine, Shim())

@app.post("/api/{engine}/generate")
async def proxy_request(engine: str, request: Request):
    if engine not in services:
        raise HTTPException(status_code=404, detail=f"Unknown engine: {engine}")

    service = services[engine]
    data = await request.json()

    proc = processes.get(engine)
    if not proc or proc.poll() is not None:
        return JSONResponse({"error": f"{engine} engine is not running"}, status_code=503)

    if engine in ("chat", "code"):
        payload = service.format_request(data)
        if not await probe_endpoint(service.get_health_endpoint()):
            return JSONResponse({"error": f"{engine} engine is not ready yet"}, status_code=503)
        return StreamingResponse(
            stream_upstream(service.get_api_endpoint(), payload),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    attempts = service.payload_attempts(data)
    errors = []
    async with httpx.AsyncClient(timeout=240.0) as client:
        for label, payload in attempts:
            try:
                logger.info("Image payload attempt: %s", label)
                resp = await client.post(service.get_api_endpoint(), json=payload)
                content_type = resp.headers.get("content-type", "application/json")
                body_text = resp.text[:1200]

                if resp.status_code < 400:
                    try:
                        parsed = resp.json()
                    except Exception:
                        return Response(content=resp.content, status_code=resp.status_code, media_type=content_type)
                    if isinstance(parsed, dict) and parsed.get("images"):
                        parsed["symon_payload_mode"] = label
                        return JSONResponse(parsed)
                    errors.append({"mode": label, "status": resp.status_code, "error": "No images field in response", "body": body_text})
                    continue

                errors.append({"mode": label, "status": resp.status_code, "error": resp.reason_phrase, "body": body_text})
            except Exception as exc:
                errors.append({"mode": label, "status": "exception", "error": repr(exc)})

    return JSONResponse(
        {
            "error": "Image generation failed after all payload modes",
            "attempts": errors,
            "hint": "Enable Compatibility mode in the Image Studio tab or check the sd-server terminal log.",
        },
        status_code=502,
    )


@app.get("/")
async def index():
    return FileResponse(ROOT / "ui" / "index.html")


app.mount("/helpers", StaticFiles(directory=str(ROOT / "helpers")), name="helpers")
app.mount("/docs-local", StaticFiles(directory=str(ROOT / "docs")), name="docs-local")
app.mount("/css", StaticFiles(directory=str(ROOT / "ui" / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(ROOT / "ui" / "js")), name="js")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
