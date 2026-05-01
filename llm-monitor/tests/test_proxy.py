"""Tests for the proxy handler."""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from src.app import app


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


class TestProxy502:
    """Test that proxy returns 502 when backend is unreachable."""

    @pytest.mark.asyncio
    async def test_proxy_returns_502_when_backend_down(self):
        """When llama.cpp is not running, proxy should return 502."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={"model": "test", "prompt": "hello"},
            )
            # Should be 502 because no backend is running
            assert response.status_code == 502
            data = response.json()
            assert "error" in data
