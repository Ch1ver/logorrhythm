"""Swarm topology one-byte opcode extensions. [EXPERIMENTAL / not hot-path]."""

from __future__ import annotations

OP_BROADCAST = 0x80
OP_MULTICAST = 0x81
OP_PIPELINE = 0x82
OP_MESH = 0x83


def broadcast(sender: str, agents: list[str], payload: str) -> dict[str, str]:
    return {agent: f"{sender}:{payload}" for agent in agents}


def multicast(sender: str, group: list[str], payload: str) -> dict[str, str]:
    return {agent: f"{sender}:{payload}" for agent in group}


def pipeline(stages: list[str], payload: str) -> str:
    out = payload
    for stage in stages:
        out = f"{stage}[{out}]"
    return out


def mesh(sender: str, peers: list[str], payload: str) -> list[tuple[str, str, str]]:
    return [(sender, peer, payload) for peer in peers]
