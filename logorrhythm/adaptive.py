"""Adaptive compression profile for recurring traffic patterns."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class AdaptiveCodec:
    """Learns repeated messages and assigns compact session aliases."""

    warmup_hits: int = 3
    _hits: Counter[str] = field(default_factory=Counter)
    _alias_to_message: dict[int, str] = field(default_factory=dict)
    _message_to_alias: dict[str, int] = field(default_factory=dict)
    _next_alias: int = 1

    def encode(self, message: str) -> bytes:
        self._hits[message] += 1
        alias = self._message_to_alias.get(message)
        if alias is not None:
            return bytes((0xA0, alias))

        if self._hits[message] >= self.warmup_hits and self._next_alias <= 255:
            alias = self._next_alias
            self._next_alias += 1
            self._message_to_alias[message] = alias
            self._alias_to_message[alias] = message
            return bytes((0xA0, alias))

        raw = message.encode("utf-8")
        return bytes((0xA1,)) + raw

    def decode(self, payload: bytes) -> str:
        if not payload:
            raise ValueError("adaptive payload cannot be empty")
        mode = payload[0]
        if mode == 0xA1:
            msg = payload[1:].decode("utf-8")
            self._hits[msg] += 1
            return msg
        if mode == 0xA0:
            if len(payload) != 2:
                raise ValueError("alias payload must be 2 bytes")
            alias = payload[1]
            if alias not in self._alias_to_message:
                raise ValueError("unknown adaptive alias")
            return self._alias_to_message[alias]
        raise ValueError(f"unknown adaptive mode: {mode}")


@dataclass(frozen=True)
class AdaptiveBenchmark:
    static_bytes: int
    adaptive_bytes: int

    @property
    def improvement_percent(self) -> float:
        return ((self.static_bytes - self.adaptive_bytes) / self.static_bytes) * 100.0


def benchmark_adaptive_vs_static(*, message: str = "HANDOFF:A1>A2", count: int = 10_000) -> AdaptiveBenchmark:
    codec = AdaptiveCodec(warmup_hits=3)
    static_bytes = 0
    adaptive_bytes = 0
    for _ in range(count):
        raw = message.encode("utf-8")
        static_bytes += len(raw)
        adaptive_bytes += len(codec.encode(message))
    return AdaptiveBenchmark(static_bytes=static_bytes, adaptive_bytes=adaptive_bytes)
