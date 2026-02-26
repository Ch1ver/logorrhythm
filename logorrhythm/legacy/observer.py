"""Structured observer-plane logging utilities."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EventLog:
    timestamp: float
    correlation_id: str
    source_id: str
    destination_id: str
    instruction: str
    payload_size_bytes: int
    total_size_bytes: int
    latency_ms: float
    status: str
    signature_verified: bool

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


def emit_event(**kwargs: object) -> EventLog:
    data = {"timestamp": kwargs.pop("timestamp", time.time()), **kwargs}
    return EventLog(**data)  # type: ignore[arg-type]
