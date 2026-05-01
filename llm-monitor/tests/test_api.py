"""Tests for the REST API endpoints."""

import os
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport
from src.app import app
from src import config
from src.storage import init_db, store_request_metric, store_system_metric


@pytest.fixture(autouse=True)
def setup_data():
    original_db = config.Config.DB_PATH
    tmp_path = tempfile.mktemp(suffix=".db")
    config.Config.DB_PATH = tmp_path
    init_db()
    store_request_metric({
        "endpoint": "/v1/chat/completions",
        "model": "test-model",
        "status_code": 200,
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "total_latency_ms": 500.0,
    })
    store_system_metric({
        "gpu_utilization": 50.0,
        "cpu_usage": 30.0,
        "gpu_memory_used_mb": 4096.0,
        "gpu_memory_total_mb": 8192.0,
        "gpu_temperature": 65.0,
        "gpu_power_watts": 200.0,
        "memory_used_mb": 4096.0,
        "memory_total_mb": 16384.0,
        "swap_used_mb": 0.0,
        "swap_total_mb": 8192.0,
    })
    yield
    config.Config.DB_PATH = original_db
    for suffix in [".db", ".db-wal", ".db-shm"]:
        p = tmp_path + suffix
        if os.path.exists(p):
            os.remove(p)


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_get_requests(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics/requests")
            assert response.status_code == 200
            data = response.json()
            assert "requests" in data
            assert data["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics/system")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert data["count"] >= 1

    @pytest.mark.asyncio
    async def test_get_summary(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics/summary")
            assert response.status_code == 200
            data = response.json()
            assert "total_requests" in data
            assert data["total_requests"] >= 1

    @pytest.mark.asyncio
    async def test_get_models(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/metrics/models")
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert "test-model" in data["models"]
