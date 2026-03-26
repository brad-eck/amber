"""FastAPI entry point for Amber."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import load_config
from backend.app.models import init_db
from backend.app.routes import router as entries_router
from backend.app.storage import ensure_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load config, ensure data dirs exist, initialize the DB."""
    cfg = load_config()
    data_path = cfg.storage.resolved_data_path

    ensure_directories(data_path)
    init_db(data_path / "amber.db")

    # Store config on app state so route handlers can access it.
    app.state.config = cfg
    app.state.data_path = data_path
    app.state.db_path = data_path / "amber.db"

    yield


app = FastAPI(
    title="Amber",
    description="Personal time capsule API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(entries_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def cli():
    """CLI entry point: run the Amber server."""
    import uvicorn

    cfg = load_config()
    uvicorn.run(
        "backend.app.main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        reload=True,
    )
