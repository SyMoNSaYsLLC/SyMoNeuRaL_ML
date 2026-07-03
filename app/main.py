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

    @app.get("/api/health")
    def legacy_health():
        return {"ok": True, "service": "SyMoNeuRaL Local ML", "engines": app.state.engine_manager.status()}

    @app.get("/")
    def index():
        return FileResponse(ROOT / "frontend" / "index.html")

    app.mount("/css", StaticFiles(directory=str(ROOT / "frontend" / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(ROOT / "frontend" / "js")), name="js")
    return app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


# Simple one-page chat frontend.
ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
STATIC_DIR = ROOT_DIR / "static"

if STATIC_DIR.exists() and "static" not in [r.name for r in app.routes]:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def simple_chat_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

