"""WebSocket transport adapter for LOGORRHYTHM payload exchange."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .api import decode, encode

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

    async def handler(ws):
        incoming = await ws.recv()
        await ws.send(incoming)

    server = await websockets.serve(handler, "127.0.0.1", port)
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            payload = encode(task=message)
            await ws.send(payload)
            response = await ws.recv()
            return decode(response)
    finally:
        server.close()
        await server.wait_closed()


def benchmark_transport(*, repeats: int = 20) -> TransportDelta:
    simulated_samples = []
    websocket_samples = []

    for _ in range(repeats):
        s0 = time.perf_counter_ns()
        packed = encode(task="bench")
        decode(packed)
        simulated_samples.append((time.perf_counter_ns() - s0) / 1_000_000)

        w0 = time.perf_counter_ns()
        asyncio.run(exchange_once(message="bench"))
        websocket_samples.append((time.perf_counter_ns() - w0) / 1_000_000)

    return TransportDelta(
        simulated_latency_ms=sum(simulated_samples) / len(simulated_samples),
        websocket_latency_ms=sum(websocket_samples) / len(websocket_samples),
    )
