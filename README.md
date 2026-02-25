# LOGORRHYTHM (v0.0.4)

<!-- BENCHMARK_TABLE_START -->
| Version | Byte Reduction | Throughput Gain | Latency Improvement | Agents Tested |
|---|---:|---:|---:|---|
| v0.0.1 | baseline | baseline | baseline | 8/64/512 |
| v0.0.2 | 22.37% | 27.62% | 21.64% | 8/64/512 |
| v0.0.3 | 24.37% | 38.87% | 25.64% | 8/64/512 |
| v0.0.4 | 29.84% | 45.73% | 31.42% | 8/64/512 |
<!-- BENCHMARK_TABLE_END -->

LOGORRHYTHM is a two-layer protocol and execution language for AI-agent speed.

## Install (PyPI)

```bash
pip install logorrhythm
```

## Minimal API

```python
from logorrhythm import encode, decode, send, receive

wire = send(task="handoff dependency graph")
assert receive(wire) == "handoff dependency graph"
```

## v0.0.4 benchmark graphs

![Byte reduction trend](benchmarks/graphs/byte_reduction_line.png)
![Throughput gain by scale](benchmarks/graphs/throughput_scale_bar.png)
![Latency distribution p50/p95](benchmarks/graphs/latency_distribution.png)

## New v0.0.4 systems

- Adaptive compression dictionary for repeated patterns (`logorrhythm.adaptive`).
- Streaming protocol primitives for start/chunk/end delivery (`logorrhythm.streaming`).
- Swarm topology primitives using one-byte opcodes: broadcast, multicast, pipeline, mesh (`logorrhythm.topology`).
- Fault-tolerance checkpoint and reassignment flow (`logorrhythm.fault_tolerance`).
- Real WebSocket transport adapter + benchmark against simulated transport (`logorrhythm.transport_ws`).
- Shared-secret identity handshake with compact session proof (`logorrhythm.identity`).

## Automation contract

Running tests auto-runs benchmark table/graph synchronization via `tests/__init__.py`; no manual `--sync-benchmark-table` call is needed.

## Commands

```bash
python -m unittest
python -m logorrhythm.cli --sync-benchmark-table
```
