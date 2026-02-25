# LOGORRHYTHM (v0.0.5)

<!-- LOGORRHYTHM_BENCHMARK_TABLE_START -->
| Version | Byte Reduction | Throughput Gain | Latency Improvement | Agents Tested |
|---|---:|---:|---:|---|
| v0.0.1 | baseline | baseline | baseline | 8/64/512 |
| v0.0.2 | 22.37% | 27.62% | 21.64% | 8/64/512 |
| v0.0.3 | 24.37% | 38.87% | 25.64% | 8/64/512 |
| v0.0.4 | 29.84% | 45.73% | 31.42% | 8/64/512 |
| v0.0.5 | 29.84% | 45.73% | 31.42% | 8/64/512 |
<!-- LOGORRHYTHM_BENCHMARK_TABLE_END -->

LOGORRHYTHM is a compact protocol and execution substrate for multi-agent communication.

## Install (PyPI)

```bash
pip install logorrhythm
```

## Minimal API

```python
from logorrhythm import encode, decode

wire = encode(task="handoff dependency graph", src="agent-A", dst="agent-B")
assert decode(wire) == "handoff dependency graph"
```

## Architecture (v0.0.5 package, mixed protocol support)

```
+----------------------+      +-----------------------+
|  API / CLI           | ---> |  Encoding Pipeline    |
|  - encode/decode     |      |  - v1 legacy compact  |
|  - inspect/tap/replay|      |  - v2 string envelope |
+----------+-----------+      +-----------+-----------+
           |                              |
           v                              v
+----------------------+      +-----------------------+
| Handshake/Registry   |      | Security + Observer   |
| - WHOAMI/CAPABILITIES|      | - correlation_id      |
| - HEARTBEAT tracking |      | - HMAC + nonce guard  |
+----------+-----------+      +-----------+-----------+
           |                              |
           +--------------+---------------+
                          v
                 +------------------+
                 | Transport Layer  |
                 | base/ws_client   |
                 | ws_server        |
                 +------------------+
```

## v0.0.5 benchmark graphs

![Byte reduction trend](docs/graphs/byte_reduction_line.svg)
![Throughput gain by scale](docs/graphs/throughput_scale_bar.svg)
![Latency distribution p50/p95](docs/graphs/latency_distribution.svg)

## Automation contract

Tests are side-effect free and do not write README or graph artifacts. Run benchmark sync explicitly (for example in CI release jobs) via `python -m logorrhythm.cli --sync-benchmark-table` and `python -m logorrhythm.cli --generate-graphs`.

## Commands

```bash
python -m unittest
python -m logorrhythm.cli inspect <encoded_message>
python -m logorrhythm.cli tap --ws
python -m logorrhythm.cli replay <logfile>
```
