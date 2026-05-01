"""WebSocket broadcaster for real-time dashboard updates."""

import json
import logging
import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

ws_router = APIRouter()


class WebSocketBroadcaster:
    """Manages connected WebSocket clients and broadcasts messages."""

    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self):
        return len(self._clients)

    async def connect(self, websocket: WebSocket):
        """Add a client to the broadcast set."""
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        logger.info(f"WebSocket client connected (total: {self.client_count})")

    async def disconnect(self, websocket: WebSocket):
        """Remove a client from the broadcast set."""
        async with self._lock:
            self._clients.discard(websocket)
        logger.info(f"WebSocket client disconnected (total: {self.client_count})")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        if not self._clients:
            return

        data = json.dumps(message)
        disconnected = set()

        async with self._lock:
            for client in self._clients:
                try:
                    await client.send_text(data)
                except Exception:
                    disconnected.add(client)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self._clients -= disconnected
            logger.info(f"Removed {len(disconnected)} disconnected clients")

    async def broadcast_request_metric(self, data: dict):
        """Broadcast a request metric event."""
        await self.broadcast({
            "type": "request_metric",
            "data": data,
        })

    async def broadcast_system_metric(self, data: dict):
        """Broadcast a system metric event."""
        await self.broadcast({
            "type": "system_metric",
            "data": data,
        })


# Global broadcaster instance
broadcaster = WebSocketBroadcaster()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive — receive ping/keepalive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await broadcaster.disconnect(websocket)
