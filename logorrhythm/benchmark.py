"""Benchmark helpers for comparing protocol iterations."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .encoding import encode_compact_payload, encode_message
from .spec import AgentCode, InstructionCode, MessageType


@dataclass(frozen=True)
class Scenario:
    src: str
    dst: str
    instruction: str
    task: str


@dataclass(frozen=True)
class ScenarioMetrics:
    name: str
    v001_chars: int
    v002_chars: int
    v001_bytes: int
    v002_bytes: int


@dataclass(frozen=True)
class BenchmarkSummary:
    scenarios: list[ScenarioMetrics]
    total_v001_chars: int
    total_v002_chars: int
    total_v001_bytes: int
    total_v002_bytes: int

    @property
    def char_reduction_percent(self) -> float:
        return ((self.total_v001_chars - self.total_v002_chars) / self.total_v001_chars) * 100.0

    @property
    def byte_reduction_percent(self) -> float:
        return ((self.total_v001_bytes - self.total_v002_bytes) / self.total_v001_bytes) * 100.0


def _v001_payload_json(s: Scenario) -> str:
    """Approximate v0.0.1 payload shape with English keys and labels."""
    return json.dumps(
        {
            "from": s.src,
            "to": s.dst,
            "instruction": s.instruction,
            "task": s.task,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _v002_transport(s: Scenario) -> str:
    payload = encode_compact_payload(
        src=AgentCode[s.src],
        dst=AgentCode[s.dst],
        instruction=InstructionCode[s.instruction],
        task=s.task,
    )
    return encode_message(message_type=MessageType.AGENT, payload=payload)


def benchmark_v001_vs_v002() -> BenchmarkSummary:
    corpus: dict[str, Scenario] = {
        "handoff_status": Scenario(
            src="A1",
            dst="A2",
            instruction="HANDOFF",
            task="Summarize latest status and continue execution.",
        ),
        "query_dependency": Scenario(
            src="A2",
            dst="A1",
            instruction="QUERY",
            task="Need dependency map for module parsing path.",
        ),
        "complete_cycle": Scenario(
            src="A1",
            dst="A2",
            instruction="COMPLETE",
            task="Task complete; attach compact trace digest.",
        ),
    }

    metrics: list[ScenarioMetrics] = []
    for name, scenario in corpus.items():
        baseline = _v001_payload_json(scenario)
        candidate = _v002_transport(scenario)
        metrics.append(
            ScenarioMetrics(
                name=name,
                v001_chars=len(baseline),
                v002_chars=len(candidate),
                v001_bytes=len(baseline.encode("utf-8")),
                v002_bytes=len(candidate.encode("utf-8")),
            )
        )

    return BenchmarkSummary(
        scenarios=metrics,
        total_v001_chars=sum(m.v001_chars for m in metrics),
        total_v002_chars=sum(m.v002_chars for m in metrics),
        total_v001_bytes=sum(m.v001_bytes for m in metrics),
        total_v002_bytes=sum(m.v002_bytes for m in metrics),
    )
