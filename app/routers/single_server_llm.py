from __future__ import annotations

import asyncio
import json
import os
import shlex
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import get_settings

router = APIRouter(tags=["SyMoNeuRaL single-server llama-ui compatibility"])
ROOT = Path(__file__).resolve().parents[2]


def _settings_raw() -> dict[str, Any]:
    try:
        return get_settings().raw
    except Exception:
        return {}


def _model_path(kind: str = "writer") -> str:
    raw = _settings_raw()
    models = raw.get("models", {}) if isinstance(raw, dict) else {}
    if kind == "code":
        return str(os.getenv("SYMON_CODE_MODEL", models.get("code_model", "./models/llm/qwen2.5-coder-1.5b-instruct-q8_0.gguf")))
    return str(os.getenv("SYMON_WRITER_MODEL", os.getenv("SYMON_MODEL", models.get("writer_model", "./models/llm/gemma-4-12b-it-Q4_K_M.gguf"))))


def _find_llama_cli() -> str:
    env = os.getenv("SYMON_LLM_CLI")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend([
        ROOT / "bin" / "symon-llm-cli",
        ROOT / "bin" / "llama-cli",
        ROOT / "engines" / "symon-llm.cpp" / "build" / "bin" / "llama-cli",
        ROOT / "engines" / "llama.cpp" / "build" / "bin" / "llama-cli",
    ])
    for p in candidates:
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return ""


def _message_prompt(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for msg in messages:
        role = str(msg.get("role", "user"))
        content = msg.get("content", "")
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        chunks.append(str(item.get("text", "")))
                    elif "text" in item:
                        chunks.append(str(item.get("text", "")))
                else:
                    chunks.append(str(item))
            content = "\n".join(chunks)
        parts.append(f"{role.upper()}: {content}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def _clean_cli_output(text: str, prompt: str) -> str:
    s = text.replace("\r\n", "\n").strip()
    # Strip common llama-cli timing chatter when it appears in stdout.
    cleaned = []
    for line in s.splitlines():
        low = line.lower().strip()
        if low.startswith(("llama_", "ggml_", "sampling", "generate:", "load_", "main:")):
            continue
        if " per token" in low or "tokens per second" in low:
            continue
        cleaned.append(line)
    s = "\n".join(cleaned).strip()
    if s.startswith(prompt):
        s = s[len(prompt):].strip()
    if "ASSISTANT:" in s:
        s = s.split("ASSISTANT:", 1)[-1].strip()
    return s or text.strip()


def _run_llama_cli(prompt: str, data: dict[str, Any]) -> str:
    cli = _find_llama_cli()
    if not cli:
        raise RuntimeError("No llama CLI found. Expected bin/symon-llm-cli or engines/symon-llm.cpp/build/bin/llama-cli")

    model = str(data.get("model") or _model_path("writer"))
    if model in {"local-model", "auto", "SyMoNeuRaL", "default"}:
        model = _model_path("writer")

    max_tokens = str(int(data.get("max_tokens") or data.get("n_predict") or os.getenv("SYMON_CLI_MAX_TOKENS", "1024")))
    temp = str(float(data.get("temperature", os.getenv("SYMON_CLI_TEMP", "0.7"))))
    top_p = str(float(data.get("top_p", os.getenv("SYMON_CLI_TOP_P", "0.95"))))
    ctx = str(os.getenv("SYMON_LLAMA_CTX", os.getenv("SYMON_CHAT_CTX", "294912")))
    batch = str(os.getenv("SYMON_LLAMA_BATCH", os.getenv("SYMON_CHAT_BATCH", "4096")))
    ubatch = str(os.getenv("SYMON_LLAMA_UBATCH", os.getenv("SYMON_CHAT_UBATCH", "512")))
    gpu_layers = str(os.getenv("SYMON_LLAMA_GPU_LAYERS", os.getenv("SYMON_CHAT_GPU_LAYERS", "999")))

    base = [cli, "-m", model, "-n", max_tokens, "--temp", temp, "--top-p", top_p, "-p", prompt]
    candidates = [
        base + ["--gpu-layers", gpu_layers, "--ctx-size", ctx, "--batch-size", batch, "--ubatch-size", ubatch, "--no-display-prompt"],
        base + ["--gpu-layers", gpu_layers, "--ctx-size", ctx, "--batch-size", batch, "--ubatch-size", ubatch],
        base + ["-ngl", gpu_layers, "-c", ctx, "-b", batch, "-ub", ubatch, "--no-display-prompt"],
        base + ["-ngl", gpu_layers, "-c", ctx, "-b", batch, "-ub", ubatch],
    ]

    timeout = int(os.getenv("SYMON_CLI_TIMEOUT", "900"))
    errors: list[str] = []
    env = os.environ.copy()
    env.setdefault("CUDA_VISIBLE_DEVICES", "0")
    env.setdefault("LLAMA_ARG_CACHE_TYPE_K", "f16")
    env.setdefault("LLAMA_ARG_CACHE_TYPE_V", "f16")

    for cmd in candidates:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return _clean_cli_output(proc.stdout, prompt)
        err = (proc.stderr or proc.stdout or "").strip()
        errors.append("$ " + " ".join(shlex.quote(x) for x in cmd[:12]) + (" ..." if len(cmd) > 12 else "") + "\n" + err[-1200:])
        # Only retry flag/parser failures; model/runtime failures should return the real error.
        low = err.lower()
        if not any(x in low for x in ["unknown", "invalid", "error while handling argument", "unrecognized"]):
            break
    raise RuntimeError("llama CLI failed:\n" + "\n---\n".join(errors))


def _model_response() -> dict[str, Any]:
    model = _model_path("writer")
    created = int(time.time())
    item = {
        "id": model,
        "object": "model",
        "created": created,
        "owned_by": "SyMoNeuRaL",
        "aliases": [model, "SyMoNeuRaL", "gemma-4"],
        "tags": [],
    }
    return {
        "object": "list",
        "data": [item],
        "models": [
            {
                "name": model,
                "model": model,
                "modified_at": "",
                "size": "",
                "digest": "",
                "type": "model",
                "description": "SyMoNeuRaL local model served by FastAPI on 127.0.0.1:8000",
                "tags": ["SyMoNeuRaL"],
                "capabilities": ["completion", "chat"],
                "parameters": "",
                "details": {"format": "gguf", "family": "gemma", "families": ["gemma"], "quantization_level": ""},
            }
        ],
    }


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "SyMoNeuRaL", "server": "127.0.0.1:8000", "engine_http_servers": False}


@router.get("/v1/models")
def v1_models() -> dict[str, Any]:
    return _model_response()


@router.get("/models")
def models() -> dict[str, Any]:
    return _model_response()


@router.get("/props")
def props(model: str | None = None, autoload: bool = False) -> dict[str, Any]:
    m = model or _model_path("writer")
    return {
        "name": "SyMoNeuRaL",
        "model": m,
        "models": _model_response()["models"],
        "total_slots": 1,
        "default_generation_settings": {
            "temperature": 0.7,
            "top_p": 0.95,
            "n_predict": 1024,
            "stream": True,
        },
        "chat_template": "SyMoNeuRaL",
        "bos_token": "",
        "eos_token": "",
        "build_info": "SyMoNeuRaL single FastAPI server",
        "engine_http_servers": False,
    }


@router.get("/tools")
def tools() -> dict[str, Any]:
    return {"tools": [], "object": "list", "server": "SyMoNeuRaL"}


@router.get("/slots")
def slots() -> list[Any]:
    return []


@router.post("/tokenize")
async def tokenize(data: dict[str, Any]) -> dict[str, Any]:
    text = str(data.get("content") or data.get("prompt") or "")
    return {"tokens": list(range(len(text.split())))}


@router.post("/detokenize")
async def detokenize(data: dict[str, Any]) -> dict[str, Any]:
    return {"content": ""}


@router.post("/completion")
async def completion(data: dict[str, Any]):
    prompt = str(data.get("prompt") or data.get("content") or "")
    if not prompt:
        return JSONResponse({"error": "prompt required"}, status_code=400)
    try:
        answer = await asyncio.to_thread(_run_llama_cli, prompt, data)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    return {"content": answer, "stop": True, "model": data.get("model") or _model_path("writer")}


@router.post("/v1/chat/completions")
async def chat_completions(data: dict[str, Any], request: Request):
    messages = data.get("messages") or []
    if not isinstance(messages, list) or not messages:
        prompt = str(data.get("prompt") or "")
        messages = [{"role": "user", "content": prompt}]
    prompt = _message_prompt(messages)
    model = str(data.get("model") or _model_path("writer"))
    stream = bool(data.get("stream", False))
    cid = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    async def compute() -> str:
        return await asyncio.to_thread(_run_llama_cli, prompt, data)

    if stream:
        async def gen():
            try:
                answer = await compute()
                chunk = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"content": answer}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n".encode()
                done = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(done)}\n\n".encode()
                yield b"data: [DONE]\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n".encode()
                yield b"data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    try:
        answer = await compute()
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    return {
        "id": cid,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
