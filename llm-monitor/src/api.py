"""Dashboard REST API endpoints."""

import logging
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Query

from src.config import Config
from src.storage import (
    get_requests,
    get_system_metrics,
    get_summary,
    get_models,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/metrics")


@api_router.get("/requests")
async def api_requests(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to"),
    model: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get request metrics with optional filtering."""
    requests = get_requests(
        start=from_date,
        end=to_date,
        model=model,
        limit=limit,
        offset=offset,
    )
    return {"requests": requests, "count": len(requests)}


@api_router.get("/system")
async def api_system(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to"),
    limit: int = Query(500, ge=1, le=5000),
):
    """Get system metrics with optional date filtering."""
    metrics = get_system_metrics(start=from_date, end=to_date, limit=limit)
    return {"metrics": metrics, "count": len(metrics)}


@api_router.get("/summary")
async def api_summary(
    from_date: str = Query(None, alias="from"),
    to_date: str = Query(None, alias="to"),
):
    """Get aggregate summary statistics."""
    summary = get_summary(start=from_date, end=to_date)

    # Add GPU/CPU availability info
    try:
        import pynvml
        pynvml.nvmlInit()
        pynvml.nvmlShutdown()
        summary["gpu_available"] = True
    except Exception:
        summary["gpu_available"] = False

    return summary


@api_router.get("/models")
async def api_models():
    """Get list of known models from request history and llama.cpp."""
    # Get from local history
    local_models = get_models()

    # Try to get from llama.cpp /props endpoint
    remote_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{Config.LLM_BACKEND_URL}/props")
            if resp.status_code == 200:
                data = resp.json()
                model_info = data.get("model", {})
                if isinstance(model_info, dict):
                    name = model_info.get("name")
                    if name:
                        remote_models.append(name)
                # Check for model list
                models_list = data.get("model", [])
                if isinstance(models_list, list):
                    for m in models_list:
                        if isinstance(m, dict):
                            name = m.get("name") or m.get("model")
                            if name:
                                remote_models.append(name)
                        elif isinstance(m, str):
                            remote_models.append(m)
    except Exception:
        pass

    all_models = list(dict.fromkeys(local_models + remote_models))  # unique, preserve order
    return {"models": all_models}
