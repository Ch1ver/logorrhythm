"""Dead-agent detection with low-overhead heartbeat windows."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class HeartbeatConfig:
    interval_s: float = 2.0
    grace_misses: int = 2


class DeadAgentDetector:
    """Marks an agent dead only after N consecutive missed heartbeat windows."""

    def __init__(self, config: HeartbeatConfig | None = None) -> None:
        self.config = config or HeartbeatConfig()
        self._last_seen: dict[str, float] = {}

    def heartbeat(self, agent_id: str, *, now: float | None = None) -> None:
        self._last_seen[agent_id] = now if now is not None else time.monotonic()

    def is_suspected_dead(self, agent_id: str, *, now: float | None = None) -> bool:
        if agent_id not in self._last_seen:
            return True
        current = now if now is not None else time.monotonic()
        elapsed = current - self._last_seen[agent_id]
        threshold = self.config.interval_s * (self.config.grace_misses + 1)
        return elapsed > threshold
