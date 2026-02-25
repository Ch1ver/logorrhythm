"""Cross-model benchmark harness.

The harness is provider-agnostic: callers inject send functions for each model API.
 [EXPERIMENTAL / not hot-path]."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ModelResult:
    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class CrossModelBenchmark:
    sender: ModelResult
    receiver: ModelResult

    @property
    def total_tokens(self) -> int:
        return self.sender.prompt_tokens + self.sender.completion_tokens + self.receiver.prompt_tokens + self.receiver.completion_tokens


ModelCall = Callable[[str], tuple[str, int, int]]


def run_cross_model_benchmark(*, encoded_payload: str, sender_model: str, receiver_model: str, sender_call: ModelCall, receiver_call: ModelCall) -> CrossModelBenchmark:
    start_sender = time.perf_counter_ns()
    mid_payload, s_prompt, s_completion = sender_call(encoded_payload)
    sender_ms = (time.perf_counter_ns() - start_sender) / 1_000_000

    start_receiver = time.perf_counter_ns()
    _, r_prompt, r_completion = receiver_call(mid_payload)
    receiver_ms = (time.perf_counter_ns() - start_receiver) / 1_000_000

    return CrossModelBenchmark(
        sender=ModelResult(model=sender_model, latency_ms=sender_ms, prompt_tokens=s_prompt, completion_tokens=s_completion),
        receiver=ModelResult(model=receiver_model, latency_ms=receiver_ms, prompt_tokens=r_prompt, completion_tokens=r_completion),
    )
