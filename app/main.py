from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers.api_v1 import router as api_v1_router
from app.routers.iptv import router as iptv_router
from app.services.process_manager import EngineProcessManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyMoNeuRaL")
ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    manager = EngineProcessManager(ROOT, settings.engines, settings.raw)
    app.state.engine_manager = manager
    await manager.start_all()
    yield
    await manager.stop_all()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SyMoNeuRaL Local ML", version="1.2.0-exclusive-vram-handoff", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.raw.get("security", {}).get("allow_origins", ["*"]),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router)
    app.include_router(iptv_router)

    @app.get("/api/health")
    def legacy_health():
        manager = getattr(app.state, "engine_manager", None)
        return {
            "ok": True,
            "service": "SyMoNeuRaL Local ML",
            "engines": manager.status() if manager else {},
        }

    frontend_dir = ROOT / "frontend"
    static_dir = ROOT / "static"
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    @app.get("/")
    def index():
        return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
