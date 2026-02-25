"""In-memory agent registry for handshake/discovery."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class AgentRecord:
    id: str
    capabilities: int
    last_seen: float


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}

    def register_agent(self, agent_id: str, capabilities: int, last_seen: float | None = None) -> AgentRecord:
        stamp = time.time() if last_seen is None else float(last_seen)
        record = AgentRecord(id=agent_id, capabilities=capabilities, last_seen=stamp)
        self._agents[agent_id] = record
        return record

    def update_heartbeat(self, agent_id: str, last_seen: float | None = None) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].last_seen = time.time() if last_seen is None else float(last_seen)

    def list_agents(self) -> list[AgentRecord]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def remove_stale_agents(self, timeout: float, now: float | None = None) -> list[str]:
        removed: list[str] = []
        current = time.time() if now is None else float(now)
        for agent_id, record in list(self._agents.items()):
            if current - record.last_seen > timeout:
                removed.append(agent_id)
                del self._agents[agent_id]
        return removed
