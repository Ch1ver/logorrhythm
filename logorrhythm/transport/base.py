"""Base transport protocol interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTransport(ABC):
    @abstractmethod
    async def send(self, payload: str) -> None:
        """Send encoded payload string."""

    @abstractmethod
    async def receive(self) -> str:
        """Receive encoded payload string."""
