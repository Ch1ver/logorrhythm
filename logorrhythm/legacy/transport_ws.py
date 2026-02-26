"""WebSocket transport adapter for LOGORRHYTHM payload exchange."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .api import decode, encode
from .transport.ws_client import WebSocketClientTransport
from .transport.ws_server import serve_echo

try:
    import websockets
except ImportError:  # pragma: no cover - optional runtime dependency
    websockets = None


@dataclass(frozen=True)
class TransportDelta:
    simulated_latency_ms: float
    websocket_latency_ms: float

    @property
    def overhead_percent(self) -> float:
        return ((self.websocket_latency_ms - self.simulated_latency_ms) / self.simulated_latency_ms) * 100.0


async def exchange_once(*, message: str = "ping", port: int = 8765) -> str:
    if websockets is None:
        raise RuntimeError("websockets dependency is required for WebSocket transport")
    server = await serve_echo("127.0.0.1", port)
    try:
        ws = await websockets.connect(f"ws://127.0.0.1:{port}")
        transport = WebSocketClientTransport(ws)
        payload = encode(task=message)
        await transport.send(payload)
        response = await transport.receive()
        await ws.close()
        return decode(response)
    finally:
        server.close()
        await server.wait_closed()


async def _benchmark_transport_async(repeats: int) -> TransportDelta:
    simulated_samples = []
    websocket_samples = []
    for _ in range(repeats):
        s0 = time.perf_counter_ns()
        packed = encode(task="bench")
        decode(packed)
        simulated_samples.append((time.perf_counter_ns() - s0) / 1_000_000)

        w0 = time.perf_counter_ns()
        await exchange_once(message="bench")
        websocket_samples.append((time.perf_counter_ns() - w0) / 1_000_000)

    return TransportDelta(
        simulated_latency_ms=sum(simulated_samples) / len(simulated_samples),
        websocket_latency_ms=sum(websocket_samples) / len(websocket_samples),
    )


def benchmark_transport(*, repeats: int = 20) -> TransportDelta:
    return asyncio.run(_benchmark_transport_async(repeats))
