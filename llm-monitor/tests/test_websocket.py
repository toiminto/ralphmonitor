"""Tests for WebSocket broadcaster."""

import asyncio
import pytest
from src.websocket import WebSocketBroadcaster


class TestWebSocketBroadcaster:
    @pytest.mark.asyncio
    async def test_broadcast_to_clients(self):
        """Verify broadcaster sends messages to connected clients."""
        broadcaster = WebSocketBroadcaster()

        # Simulate connected clients
        received = []

        class MockWebSocket:
            def __init__(self, idx):
                self.idx = idx

            async def send_text(self, data):
                received.append((self.idx, data))

        client1 = MockWebSocket(1)
        client2 = MockWebSocket(2)

        # Connect clients manually (skip accept)
        async with broadcaster._lock:
            broadcaster._clients.add(client1)
            broadcaster._clients.add(client2)

        assert broadcaster.client_count == 2

        # Broadcast
        await broadcaster.broadcast({"type": "test", "data": "hello"})

        assert len(received) == 2
        # Both clients should have received the message (order not guaranteed with sets)
        client_ids = {r[0] for r in received}
        assert client_ids == {1, 2}

    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self):
        """Verify disconnected clients are removed."""
        broadcaster = WebSocketBroadcaster()

        class MockWebSocket:
            async def send_text(self, data):
                pass

        client = MockWebSocket()
        async with broadcaster._lock:
            broadcaster._clients.add(client)

        assert broadcaster.client_count == 1

        await broadcaster.disconnect(client)
        assert broadcaster.client_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self):
        """Verify broadcast cleans up clients that error."""
        broadcaster = WebSocketBroadcaster()

        class GoodClient:
            async def send_text(self, data):
                pass

        class BadClient:
            async def send_text(self, data):
                raise Exception("disconnected")

        good = GoodClient()
        bad = BadClient()

        async with broadcaster._lock:
            broadcaster._clients.add(good)
            broadcaster._clients.add(bad)

        assert broadcaster.client_count == 2

        await broadcaster.broadcast({"type": "test"})

        # Bad client should be removed
        assert broadcaster.client_count == 1
