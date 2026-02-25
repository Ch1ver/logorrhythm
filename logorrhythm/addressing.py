"""Scalable agent addressing for LOGORRHYTHM v0.0.3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentAddress:
    """Global agent address for large multi-model swarms.

    Format: `<region>/<node>/<model>/<shard>/<agent>`
    Example: `us-east-1/n17/gpt-5/3/1042`
    """

    region: str
    node: str
    model: str
    shard: int
    agent: int

    def __post_init__(self) -> None:
        if self.shard < 0:
            raise ValueError("shard must be >= 0")
        if self.agent < 0:
            raise ValueError("agent must be >= 0")

    def encode(self) -> str:
        return f"{self.region}/{self.node}/{self.model}/{self.shard}/{self.agent}"

    @classmethod
    def decode(cls, value: str) -> "AgentAddress":
        parts = value.split("/")
        if len(parts) != 5:
            raise ValueError("address must have 5 slash-separated segments")
        region, node, model, shard, agent = parts
        return cls(region=region, node=node, model=model, shard=int(shard), agent=int(agent))


class AddressBook:
    """Compact deterministic addressing map for wire transport."""

    def __init__(self) -> None:
        self._to_id: dict[str, int] = {}
        self._from_id: dict[int, str] = {}

    def register(self, address: AgentAddress) -> int:
        encoded = address.encode()
        if encoded in self._to_id:
            return self._to_id[encoded]
        identifier = len(self._to_id) + 1
        self._to_id[encoded] = identifier
        self._from_id[identifier] = encoded
        return identifier

    def resolve(self, identifier: int) -> AgentAddress:
        return AgentAddress.decode(self._from_id[identifier])
