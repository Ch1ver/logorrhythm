"""Capability negotiation helpers."""

from __future__ import annotations

from enum import IntFlag


class Capability(IntFlag):
    STREAMING = 1 << 0
    SECURE_ENVELOPE = 1 << 1
    ADAPTIVE_ALIASING = 1 << 2
    HEARTBEAT = 1 << 3
    TRANSPORT_WS = 1 << 4


def supports(capabilities: int, required: Capability) -> bool:
    return bool(capabilities & int(required))


def negotiate(local: int, peer: int) -> int:
    """Return mutually supported capability bitmask."""
    return local & peer
