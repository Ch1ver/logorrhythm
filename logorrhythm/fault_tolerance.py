"""Checkpoint and reassignment primitives."""

from __future__ import annotations

from dataclasses import dataclass


OP_CHECKPOINT = 0x90
OP_REASSIGN = 0x91


@dataclass(frozen=True)
class Checkpoint:
    task_id: str
    owner: str
    step: int
    state: str


class CheckpointStore:
    def __init__(self) -> None:
        self._store: dict[str, Checkpoint] = {}

    def snapshot(self, checkpoint: Checkpoint) -> bytes:
        self._store[checkpoint.task_id] = checkpoint
        wire = "|".join([checkpoint.task_id, checkpoint.owner, str(checkpoint.step), checkpoint.state])
        return wire.encode("utf-8")

    def restore(self, payload: bytes) -> Checkpoint:
        task_id, owner, step, state = payload.decode("utf-8").split("|", 3)
        cp = Checkpoint(task_id=task_id, owner=owner, step=int(step), state=state)
        self._store[task_id] = cp
        return cp

    def reassign(self, task_id: str, replacement_agent: str) -> Checkpoint:
        cp = self._store[task_id]
        replacement = Checkpoint(task_id=cp.task_id, owner=replacement_agent, step=cp.step, state=cp.state)
        self._store[task_id] = replacement
        return replacement
