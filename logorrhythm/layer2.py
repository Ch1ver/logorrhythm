"""Layer 2 primitive registry and compactness helpers."""

from __future__ import annotations

from dataclasses import dataclass

V002_OPS = ("R", "S", "C", "B", "L", "K", "N", "T", "F", "E")
V003_OPS = V002_OPS + (
    "Q",  # confidence branch
    "P",  # parallel fan-out
    "J",  # join
    "H",  # model handoff
    "W",  # working memory scope
    "M",  # long-term memory scope
    "Y",  # shared swarm memory scope
)


@dataclass(frozen=True)
class ProgramDelta:
    python_chars: int
    layer2_chars: int

    @property
    def reduction_percent(self) -> float:
        return ((self.python_chars - self.layer2_chars) / self.python_chars) * 100.0


def estimate_token_delta(*, python_program: str, layer2_program: str) -> ProgramDelta:
    return ProgramDelta(python_chars=len(python_program), layer2_chars=len(layer2_program))
