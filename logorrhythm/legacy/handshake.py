"""Handshake and discovery protocol primitives."""

from __future__ import annotations

from dataclasses import dataclass

from .capabilities import negotiate
from .registry import AgentRegistry


@dataclass(frozen=True)
class HandshakeState:
    local_id: str
    peer_id: str
    local_capabilities: int
    peer_capabilities: int
    negotiated_capabilities: int


def perform_handshake(*, registry: AgentRegistry, local_id: str, peer_id: str, local_capabilities: int, peer_capabilities: int, last_seen: float) -> HandshakeState:
    """Emulate WHOAMI + CAPABILITIES exchange and registry update."""
    registry.register_agent(peer_id, peer_capabilities, last_seen=last_seen)
    return HandshakeState(
        local_id=local_id,
        peer_id=peer_id,
        local_capabilities=local_capabilities,
        peer_capabilities=peer_capabilities,
        negotiated_capabilities=negotiate(local_capabilities, peer_capabilities),
    )
