"""v0.0.3 planning and simulation helpers.

This module builds a reportable dashboard that compares an approximate
v0.0.1 JSON transport path against the v0.0.2 compact wire format while
simulating multi-agent communication volume.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from dataclasses import dataclass

from .encoding import decode_compact_payload, decode_message, encode_compact_payload, encode_message
from .spec import AgentCode, InstructionCode, MessageType


@dataclass(frozen=True)
class IterationMetrics:
    label: str
    total_messages: int
    total_bytes: int
    avg_encode_decode_ms: float
    p95_encode_decode_ms: float
    throughput_msgs_per_sec: float


@dataclass(frozen=True)
class ScaleResult:
    agent_count: int
    baseline: IterationMetrics
    candidate: IterationMetrics

    @property
    def throughput_gain_percent(self) -> float:
        return ((self.candidate.throughput_msgs_per_sec - self.baseline.throughput_msgs_per_sec) / self.baseline.throughput_msgs_per_sec) * 100.0

    @property
    def avg_latency_reduction_percent(self) -> float:
        return ((self.baseline.avg_encode_decode_ms - self.candidate.avg_encode_decode_ms) / self.baseline.avg_encode_decode_ms) * 100.0

    @property
    def byte_reduction_percent(self) -> float:
        return ((self.baseline.total_bytes - self.candidate.total_bytes) / self.baseline.total_bytes) * 100.0


@dataclass(frozen=True)
class V003Dashboard:
    scale_results: list[ScaleResult]
    recommendations: list[str]
    security_posture: list[str]

    def to_markdown(self) -> str:
        lines = [
            "# LOGORRHYTHM v0.0.3 Iteration Dashboard",
            "",
            "## Communication Performance (simulated load)",
            "",
            "| Agents | Messages | Baseline avg ms | v0.0.2 avg ms | Latency improvement | Baseline throughput msg/s | v0.0.2 throughput msg/s | Throughput gain | Byte reduction |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for result in self.scale_results:
            lines.append(
                "| "
                f"{result.agent_count} | {result.candidate.total_messages} | "
                f"{result.baseline.avg_encode_decode_ms:.4f} | {result.candidate.avg_encode_decode_ms:.4f} | "
                f"{result.avg_latency_reduction_percent:.2f}% | "
                f"{result.baseline.throughput_msgs_per_sec:.0f} | {result.candidate.throughput_msgs_per_sec:.0f} | "
                f"{result.throughput_gain_percent:.2f}% | {result.byte_reduction_percent:.2f}% |"
            )

        lines.extend(
            [
                "",
                "## Hyperdrive v0.0.3 Framework",
                "",
                *[f"- {item}" for item in self.recommendations],
                "",
                "## Shields (security hardening status)",
                "",
                *[f"- {item}" for item in self.security_posture],
            ]
        )
        return "\n".join(lines)


def _v001_round_trip(src: str, dst: str, instruction: str, task: str) -> tuple[int, float]:
    started = time.perf_counter_ns()
    encoded = json.dumps(
        {"from": src, "to": dst, "instruction": instruction, "task": task},
        separators=(",", ":"),
        sort_keys=True,
    )
    decoded = json.loads(encoded)
    if decoded["task"] != task:
        raise RuntimeError("Baseline transport corruption detected")
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return len(encoded.encode("utf-8")), elapsed_ms


def _v002_round_trip(src: str, dst: str, instruction: str, task: str) -> tuple[int, float]:
    started = time.perf_counter_ns()
    payload = encode_compact_payload(
        src=AgentCode[src],
        dst=AgentCode[dst],
        instruction=InstructionCode[instruction],
        task=task,
    )
    encoded = encode_message(message_type=MessageType.AGENT, payload=payload)
    decoded_msg = decode_message(encoded)
    decoded_payload = decode_compact_payload(decoded_msg.payload)
    if decoded_payload.task != task:
        raise RuntimeError("v0.0.2 transport corruption detected")
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return len(encoded.encode("utf-8")), elapsed_ms


def _run_simulation(agent_count: int, messages_per_agent: int, seed: int) -> ScaleResult:
    rng = random.Random(seed)
    agents = ["A1", "A2"]
    instructions = ["HANDOFF", "QUERY", "COMPLETE", "ACKNOWLEDGE"]
    tasks = [
        "sync status vector and continue workstream",
        "return dependency digest for parser lane",
        "handoff shard checksum + next action pointer",
        "publish partial result for deterministic merge",
    ]

    baseline_times: list[float] = []
    candidate_times: list[float] = []
    baseline_bytes = 0
    candidate_bytes = 0

    total_messages = agent_count * messages_per_agent
    for _ in range(total_messages):
        src = agents[rng.randrange(len(agents))]
        dst = "A2" if src == "A1" else "A1"
        instruction = instructions[rng.randrange(len(instructions))]
        task = tasks[rng.randrange(len(tasks))]

        b_bytes, b_ms = _v001_round_trip(src, dst, instruction, task)
        c_bytes, c_ms = _v002_round_trip(src, dst, instruction, task)
        baseline_times.append(_project_end_to_end_ms(b_ms, b_bytes, agent_count))
        candidate_times.append(_project_end_to_end_ms(c_ms, c_bytes, agent_count))
        baseline_bytes += b_bytes
        candidate_bytes += c_bytes

    baseline_total_s = sum(baseline_times) / 1000
    candidate_total_s = sum(candidate_times) / 1000

    baseline = IterationMetrics(
        label="v0.0.1 baseline",
        total_messages=total_messages,
        total_bytes=baseline_bytes,
        avg_encode_decode_ms=statistics.fmean(baseline_times),
        p95_encode_decode_ms=_percentile(baseline_times, 95),
        throughput_msgs_per_sec=total_messages / baseline_total_s,
    )
    candidate = IterationMetrics(
        label="v0.0.2 candidate",
        total_messages=total_messages,
        total_bytes=candidate_bytes,
        avg_encode_decode_ms=statistics.fmean(candidate_times),
        p95_encode_decode_ms=_percentile(candidate_times, 95),
        throughput_msgs_per_sec=total_messages / candidate_total_s,
    )
    return ScaleResult(agent_count=agent_count, baseline=baseline, candidate=candidate)



def _project_end_to_end_ms(codec_ms: float, message_bytes: int, agent_count: int) -> float:
    """Approximate full-lane communication latency from codec cost + wire cost + queueing."""
    bytes_per_ms = 220.0
    queue_penalty_ms = (agent_count / 1024.0) * 0.08
    transport_ms = message_bytes / bytes_per_ms
    return codec_ms + transport_ms + queue_penalty_ms

def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    idx = int((percentile / 100) * (len(ordered) - 1))
    return ordered[idx]


def build_v003_dashboard(
    *,
    agent_counts: tuple[int, ...] = (8, 64, 512),
    messages_per_agent: int = 25,
    seed: int = 7,
) -> V003Dashboard:
    if messages_per_agent <= 0:
        raise ValueError("messages_per_agent must be > 0")
    if any(count <= 0 for count in agent_counts):
        raise ValueError("agent_counts entries must all be > 0")

    scale_results = [
        _run_simulation(agent_count=count, messages_per_agent=messages_per_agent, seed=seed + i)
        for i, count in enumerate(agent_counts)
    ]

    recommendations = [
        "Add chunked transport frames and sequence IDs so long outputs do not block lanes.",
        "Implement adaptive backpressure (credit-based or token bucket) before introducing external network adapters.",
        "Publish p50/p95 latency, throughput, and error rate to a dashboard endpoint for each agent cohort.",
        "Introduce deterministic fan-out/fan-in primitives to support thousand-agent orchestration.",
        "Gate every release on benchmark regressions and conformance fixtures in CI.",
    ]

    security_posture = [
        "Current hull: CRC32 integrity + strict payload length checks detect corruption in transit.",
        "Current hull: capability bit validation and rejected compression flag reduce ambiguous parsing surface.",
        "Next shield: add authenticated signatures (SIGNED capability) before hostile-network deployments.",
        "Next shield: enforce branch protection, required CI checks, and signed commits for repo hardening.",
        "Next shield: define secret scanning and dependency-audit automation in CI.",
    ]

    return V003Dashboard(
        scale_results=scale_results,
        recommendations=recommendations,
        security_posture=security_posture,
    )
