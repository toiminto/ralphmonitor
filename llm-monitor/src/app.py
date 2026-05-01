"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config import Config
from src.storage import init_db
from src.proxy import proxy_router
from src.api import api_router
from src.websocket import ws_router
from src.pollers import start_pollers, stop_pollers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB, start pollers on startup."""
    logger.info("Initializing LLM Monitor")
    init_db()
    await start_pollers()
    yield
    await stop_pollers()
    logger.info("Shutting down LLM Monitor")


app = FastAPI(
    title="LLM Performance Monitor",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — local trusted network
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(proxy_router)
app.include_router(api_router)
app.include_router(ws_router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML."""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())
