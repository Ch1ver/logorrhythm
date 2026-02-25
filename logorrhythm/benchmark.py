"""Benchmark helpers for comparing transport efficiency and hot-path performance."""

from __future__ import annotations

import json
import time
import tracemalloc
from dataclasses import dataclass

from .adaptive import AdaptiveCodec, benchmark_adaptive_exchange
from .encoding import decode_message, encode_compact_payload, encode_message
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
    json_chars: int
    b64_chars: int
    binary_bytes: int
    json_bytes: int
    b64_bytes: int


@dataclass(frozen=True)
class BenchmarkSummary:
    scenarios: list[ScenarioMetrics]
    total_json_chars: int
    total_b64_chars: int
    total_binary_bytes: int
    total_json_bytes: int
    total_b64_bytes: int

    @property
    def char_reduction_percent(self) -> float:
        return ((self.total_json_chars - self.total_b64_chars) / self.total_json_chars) * 100.0

    @property
    def byte_reduction_percent(self) -> float:
        return ((self.total_json_bytes - self.total_binary_bytes) / self.total_json_bytes) * 100.0


@dataclass(frozen=True)
class ThroughputMetrics:
    encode_messages_per_sec: float
    decode_messages_per_sec: float


@dataclass(frozen=True)
class MemoryMicroBenchmark:
    avg_bytes_per_message: float
    avg_allocations_per_message: float


@dataclass(frozen=True)
class TokenScenario:
    name: str
    json_tokens: int
    base64_tokens: int
    adaptive_tokens: int

    @property
    def base64_savings_percent(self) -> float:
        return ((self.json_tokens - self.base64_tokens) / self.json_tokens) * 100.0 if self.json_tokens else 0.0

    @property
    def adaptive_savings_percent(self) -> float:
        return ((self.json_tokens - self.adaptive_tokens) / self.json_tokens) * 100.0 if self.json_tokens else 0.0


@dataclass(frozen=True)
class TokenBenchmarkReport:
    scenarios: list[TokenScenario]
    runs: int

    @property
    def avg_json_tokens(self) -> float:
        return sum(s.json_tokens for s in self.scenarios) / len(self.scenarios)

    @property
    def avg_base64_tokens(self) -> float:
        return sum(s.base64_tokens for s in self.scenarios) / len(self.scenarios)

    @property
    def avg_adaptive_tokens(self) -> float:
        return sum(s.adaptive_tokens for s in self.scenarios) / len(self.scenarios)


def _v001_payload_json(s: Scenario) -> str:
    return json.dumps(
        {"from": s.src, "to": s.dst, "instruction": s.instruction, "task": s.task},
        separators=(",", ":"),
        sort_keys=True,
    )


def _encoded_forms(s: Scenario) -> tuple[str, bytes]:
    payload = encode_compact_payload(
        src=AgentCode[s.src],
        dst=AgentCode[s.dst],
        instruction=InstructionCode[s.instruction],
        task=s.task,
    )
    binary = encode_message(message_type=MessageType.AGENT, payload=payload)
    base64 = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
    return base64, binary


def benchmark_v001_vs_v002() -> BenchmarkSummary:
    corpus: dict[str, Scenario] = {
        "handoff_status": Scenario("A1", "A2", "HANDOFF", "Summarize latest status and continue execution."),
        "query_dependency": Scenario("A2", "A1", "QUERY", "Need dependency map for module parsing path."),
        "complete_cycle": Scenario("A1", "A2", "COMPLETE", "Task complete; attach compact trace digest."),
    }

    metrics: list[ScenarioMetrics] = []
    for name, scenario in corpus.items():
        baseline = _v001_payload_json(scenario)
        b64, binary = _encoded_forms(scenario)
        metrics.append(
            ScenarioMetrics(
                name=name,
                json_chars=len(baseline),
                b64_chars=len(b64),
                binary_bytes=len(binary),
                json_bytes=len(baseline.encode("utf-8")),
                b64_bytes=len(b64.encode("utf-8")),
            )
        )

    return BenchmarkSummary(
        scenarios=metrics,
        total_json_chars=sum(m.json_chars for m in metrics),
        total_b64_chars=sum(m.b64_chars for m in metrics),
        total_binary_bytes=sum(m.binary_bytes for m in metrics),
        total_json_bytes=sum(m.json_bytes for m in metrics),
        total_b64_bytes=sum(m.b64_bytes for m in metrics),
    )


def benchmark_encode_decode_throughput(*, iterations: int = 20_000) -> ThroughputMetrics:
    payload = encode_compact_payload(src=AgentCode.A1, dst=AgentCode.A2, instruction=InstructionCode.HANDOFF, task="ping")

    start = time.perf_counter()
    for _ in range(iterations):
        encode_message(message_type=MessageType.AGENT, payload=payload)
    encode_elapsed = time.perf_counter() - start

    wire = encode_message(message_type=MessageType.AGENT, payload=payload)
    start = time.perf_counter()
    for _ in range(iterations):
        decode_message(wire)
    decode_elapsed = time.perf_counter() - start

    return ThroughputMetrics(
        encode_messages_per_sec=iterations / encode_elapsed if encode_elapsed else 0.0,
        decode_messages_per_sec=iterations / decode_elapsed if decode_elapsed else 0.0,
    )


def benchmark_decode_cpu_before_after(*, iterations: int = 10_000) -> tuple[float, float]:
    payload = encode_compact_payload(src=AgentCode.A1, dst=AgentCode.A2, instruction=InstructionCode.HANDOFF, task="ping")
    wire = encode_message(message_type=MessageType.AGENT, payload=payload)

    start = time.perf_counter()
    for _ in range(iterations):
        decoded = decode_message(wire)
        _ = decoded.payload
    eager_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        decoded = decode_message(wire)
        _ = decoded.payload_view
    lazy_elapsed = time.perf_counter() - start

    return eager_elapsed, lazy_elapsed


def benchmark_memory_allocations(*, iterations: int = 2000) -> MemoryMicroBenchmark:
    payload = encode_compact_payload(src=AgentCode.A1, dst=AgentCode.A2, instruction=InstructionCode.HANDOFF, task="ping")
    wire = encode_message(message_type=MessageType.AGENT, payload=payload)
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    for _ in range(iterations):
        _ = decode_message(wire).payload_view
    after = tracemalloc.take_snapshot()
    stats = after.compare_to(before, "lineno")
    allocated_bytes = sum(max(0, s.size_diff) for s in stats)
    allocated_blocks = sum(max(0, s.count_diff) for s in stats)
    tracemalloc.stop()
    return MemoryMicroBenchmark(
        avg_bytes_per_message=allocated_bytes / iterations,
        avg_allocations_per_message=allocated_blocks / iterations,
    )


def _count_tokens(text: str) -> int:
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # deterministic fallback proxy (roughly 4 chars/token)
        return max(1, (len(text) + 3) // 4)


def _scenario_payloads() -> dict[str, str]:
    return {
        "single_control": json.dumps({"op": "ACK", "task": "ok"}, separators=(",", ":"), sort_keys=True),
        "repeated_coordination": json.dumps(
            {"opcodes": ["H", "Q", "H", "C", "A"], "from": "A1", "to": "A2"},
            separators=(",", ":"),
            sort_keys=True,
        ),
        "structured_payload": json.dumps(
            {"instruction": "HANDOFF", "state": {"deps": ["parser", "lexer", "tokenizer"], "priority": 3, "retry": False}},
            separators=(",", ":"),
            sort_keys=True,
        ),
        "nested_payload": json.dumps(
            {"meta": {"trace": {"id": "abcd-1234", "span": {"parent": "root", "depth": 3}}}, "task": "merge"},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }


def benchmark_tokens(*, runs: int = 5) -> TokenBenchmarkReport:
    payloads = _scenario_payloads()
    aggregate: dict[str, tuple[int, int, int]] = {name: (0, 0, 0) for name in payloads}

    for _ in range(runs):
        adaptive = AdaptiveCodec(warmup_hits=2)
        for name, json_payload in payloads.items():
            base64_wire = encode_message(
                message_type=MessageType.AGENT,
                payload=json_payload.encode("utf-8"),
                transport_base64=True,
            )
            adaptive.encode(json_payload)
            adaptive_wire = adaptive.encode(json_payload).hex()
            j, b, a = aggregate[name]
            aggregate[name] = (
                j + _count_tokens(json_payload),
                b + _count_tokens(base64_wire),
                a + _count_tokens(adaptive_wire),
            )

    scenarios = [
        TokenScenario(name, json_tokens=j // runs, base64_tokens=b // runs, adaptive_tokens=a // runs)
        for name, (j, b, a) in aggregate.items()
    ]
    return TokenBenchmarkReport(scenarios=scenarios, runs=runs)


def benchmark_adaptive_repeated_exchange_percent(*, count: int = 10_000) -> float:
    return benchmark_adaptive_exchange(count=count).improvement_percent
