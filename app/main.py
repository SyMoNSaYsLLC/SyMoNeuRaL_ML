from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers.api_v1 import router as api_v1_router
from app.services.process_manager import EngineProcessManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyMoNeuRaL")
ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
ENGINE_BASE = os.getenv("SYMON_INTERNAL_LLM_BASE", "http://127.0.0.1:18080").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    manager = EngineProcessManager(ROOT, settings.engines, settings.raw)
    app.state.engine_manager = manager
    await manager.start_all()
    try:
        yield
    finally:
        await manager.stop_all()


def _mount_if_exists(app: FastAPI, route: str, path: Path, name: str) -> None:
    if path.exists():
        app.mount(route, StaticFiles(directory=str(path)), name=name)


async def _proxy_to_engine(path: str, request: Request) -> Response:
    target = f"{ENGINE_BASE}/{path.lstrip('/')}"
    if request.url.query:
        target += f"?{request.url.query}"
    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "connection"}
    }
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            upstream = await client.request(request.method, target, content=body, headers=headers)
    except httpx.ConnectError:
        return JSONResponse(
            {"ok": False, "error": "internal SyMoNeuRaL engine is not ready yet", "engine": ENGINE_BASE},
            status_code=503,
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers={k: v for k, v in upstream.headers.items() if k.lower() not in {"content-length", "transfer-encoding", "connection"}},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SyMoNeuRaL", version="1.6.0-single-8000", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.raw.get("security", {}).get("allow_origins", ["*"]),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # SyMoNeuRaL API remains on 8000.
    app.include_router(api_v1_router)
    try:
        from app.routers.iptv import router as iptv_router
        app.include_router(iptv_router)
    except Exception as exc:
        logger.debug("IPTV router not loaded: %s", exc)

    @app.get("/api/health")
    def legacy_health():
        manager = getattr(app.state, "engine_manager", None)
        return {
            "ok": True,
            "service": "SyMoNeuRaL",
            "public_server": "http://127.0.0.1:8000",
            "internal_engine": ENGINE_BASE,
            "engines": manager.status() if manager else {},
        }

    # Static assets for the llama-ui-style Web UI.
    _mount_if_exists(app, "/_app", FRONTEND_DIR / "_app", "frontend_app")
    _mount_if_exists(app, "/assets", FRONTEND_DIR / "assets", "frontend_assets")
    _mount_if_exists(app, "/static", ROOT / "static", "static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    # Common root files used by the generated UI/PWA.
    @app.get("/{filename}")
    async def frontend_root_file(filename: str, request: Request):
        if filename.startswith("api"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = FRONTEND_DIR / filename
        if candidate.is_file():
            return FileResponse(candidate)
        # fall through to engine for llama-ui single-file endpoints such as /props
        return await _proxy_to_engine(filename, request)

    # OpenAI-compatible and llama.cpp UI endpoints exposed through 8000 only.
    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy_v1(path: str, request: Request):
        return await _proxy_to_engine(f"v1/{path}", request)

    for route in [
        "/completion",
        "/chat/completion",
        "/tokenize",
        "/detokenize",
        "/embedding",
        "/embeddings",
        "/rerank",
        "/props",
        "/slots",
        "/metrics",
        "/health",
    ]:
        app.add_api_route(route, lambda request, route=route: _proxy_to_engine(route, request), methods=["GET", "POST", "OPTIONS"])

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
