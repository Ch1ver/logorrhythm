"""Minimal in-memory bus for demonstration purposes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentBus:
    """Store transport messages by recipient for local simulation."""

    _mailboxes: dict[str, list[str]] = field(default_factory=dict)

    def send(self, recipient: str, encoded_message: str) -> None:
        self._mailboxes.setdefault(recipient, []).append(encoded_message)

    def receive(self, recipient: str) -> list[str]:
        return self._mailboxes.pop(recipient, [])
