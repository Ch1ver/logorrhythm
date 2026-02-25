# LOGORRHYTHM ROADMAP

## v0.0.1 (complete)

- Binary wire skeleton established.
- Base64url transport + CRC32 integrity.
- Strict payload length checks.
- Python reference implementation and tests.

## v0.0.2 (this release)

- Compact positional payload encoding (no English field names).
- Single-byte agent IDs and instruction opcodes.
- Proxy benchmark path (char/byte/word) when tokenizer is unavailable.
- First Layer 2 primitive instruction sketch (10 ops).
- Formal protocol spec published in `SPEC.md`.

## v0.0.3 (target)

- Streaming/chunked message frames for long-running tasks.
- Sequence IDs + continuation opcodes.
- Partial-result delivery with deterministic reassembly.
- Backpressure signaling and timeout semantics.
- Transport adapters beyond in-memory simulation (first practical inter-agent lane).
- Scale dashboard with latency/throughput/byte metrics for reportable agent-cohort performance.
- Security hardening baseline (repo shields + signed transport planning).

### v0.0.3 release gate (hard requirement)

v0.0.3 does **not** ship unless both are true:

1. **Correctness:** all conformance tests pass, including chunk ordering/reassembly and timeout semantics.
2. **Improvement:** benchmark suite shows net communication footprint reduction vs v0.0.2 for supported scenarios (excluding framework overhead where explicitly exempted).

## v0.0.4 (target)

- Binary dictionary mode for repeated task phrases.
- Optional negotiated compression profile (if and only if net token gain is proven).
- Capability negotiation hardening tests.

## v0.1.0 (target)

- Stable Layer 2 draft syntax and parser.
- Deterministic execution semantics for core ops.
- Conformance fixtures for multi-language implementations.
- Performance harness for instruction-stream cost tracking.

## v0.5.0 (target)

- Cross-model compatibility suite.
- Multi-agent routing primitives (fan-out, merge, quorum patterns).
- Signed transport profile for hostile network environments.

## v1.0.0 (target)

- Full two-layer system release:
  - Layer 1: stable high-efficiency transport protocol.
  - Layer 2: stable compressed execution language.
- Multi-model swarm support and interoperability certification.
- Long-term versioning + migration guarantees.

## Gating Principle

A version does not ship unless benchmark deltas demonstrate measurable reduction in communication footprint without violating correctness.

## Flavor note: Starfleet + FTL ops board

Our benchmark board is the "warp readiness panel": if a new release cannot beat the previous lane in measurable signal efficiency, we do not engage warp. No parasect drift, no subspace excuses.
