from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers.api_v1 import router as api_v1_router
from app.routers.single_server_llm import router as single_server_llm_router
from app.services.process_manager import EngineProcessManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyMoNeuRaL")
ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    manager = EngineProcessManager(ROOT, settings.engines, settings.raw)
    app.state.engine_manager = manager
    # TRUE single-server mode: do not start symon-llm-server / llama-server / sd-server listeners.
    # Model work is executed by FastAPI routes using CLI subprocesses, so 127.0.0.1:8000 is the only HTTP server.
    yield
    await manager.stop_all()


def _mount_if_exists(app: FastAPI, route: str, path: Path, name: str) -> None:
    if path.exists():
        app.mount(route, StaticFiles(directory=str(path)), name=name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SyMoNeuRaL", version="1.7.0-true-single-server", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.raw.get("security", {}).get("allow_origins", ["http://127.0.0.1:8000"]),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Same-origin llama-ui compatibility API must be registered before static fallback.
    app.include_router(single_server_llm_router)
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
            "server": "http://127.0.0.1:8000",
            "single_http_server": True,
            "engine_http_servers": False,
            "engines": manager.status() if manager else {},
        }

    _mount_if_exists(app, "/_app", FRONTEND_DIR / "_app", "frontend_app")
    _mount_if_exists(app, "/assets", FRONTEND_DIR / "assets", "frontend_assets")
    _mount_if_exists(app, "/static", ROOT / "static", "static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{filename}")
    def frontend_root_file(filename: str):
        candidate = FRONTEND_DIR / filename
        if candidate.is_file():
            return FileResponse(candidate)
        return JSONResponse({"detail": "Not found"}, status_code=404)

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
