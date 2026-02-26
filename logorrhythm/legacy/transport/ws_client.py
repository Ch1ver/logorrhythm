"""WebSocket client transport implementation."""

from __future__ import annotations

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

from .base import BaseTransport


class WebSocketClientTransport(BaseTransport):
    def __init__(self, websocket):
        self._ws = websocket

    async def send(self, payload: str) -> None:
        await self._ws.send(payload)

    async def receive(self) -> str:
        return await self._ws.recv()


async def connect(uri: str):
    if websockets is None:
        raise RuntimeError("websockets dependency is required")
    ws = await websockets.connect(uri)
    return WebSocketClientTransport(ws)
