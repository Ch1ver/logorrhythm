"""WebSocket server transport implementation."""

from __future__ import annotations

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None

from .base import BaseTransport


class WebSocketServerTransport(BaseTransport):
    def __init__(self, websocket):
        self._ws = websocket

    async def send(self, payload: str) -> None:
        await self._ws.send(payload)

    async def receive(self) -> str:
        return await self._ws.recv()


async def serve_echo(host: str = "127.0.0.1", port: int = 8765):
    if websockets is None:
        raise RuntimeError("websockets dependency is required")

    async def handler(ws):
        transport = WebSocketServerTransport(ws)
        payload = await transport.receive()
        await transport.send(payload)

    return await websockets.serve(handler, host, port)
