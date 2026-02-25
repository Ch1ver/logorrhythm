# LOGORRHYTHM (v0.0.3)

LOGORRHYTHM is a two-layer protocol and execution language for AI-agent speed.

<!-- BENCHMARK_TABLE_START -->
| Version | Byte Reduction | Throughput Gain | Latency Improvement | Agents Tested |
|---|---:|---:|---:|---|
| v0.0.1 | baseline | baseline | baseline | 8/64/512 |
| v0.0.2 | 22.37% | 27.62% | 21.64% | 8/64/512 |
| v0.0.3 | 24.37% | 38.87% | 25.64% | 8/64/512 |
<!-- BENCHMARK_TABLE_END -->

The benchmark table is the release truth and is auto-synced on test runs via:

```bash
python -m logorrhythm.cli --sync-benchmark-table
```

## v0.0.3 delivered

- **Chunked transport with sequence IDs**: large payloads are split into deterministic frames and reassembled by sequence index (`logorrhythm.chunking`).
- **Scalable agent addressing**: five-segment global addresses (`region/node/model/shard/agent`) with compact address-book IDs (`logorrhythm.addressing`).
- **Dead-agent detection**: heartbeat windows + grace misses (no false positive on one miss) via `DeadAgentDetector`.
- **Layer 2 expansion**: adds confidence branch (`Q`), parallel fan-out/join (`P`/`J`), model handoff (`H`), and scoped memory ops (`W`/`M`/`Y`).
- **Cross-model benchmark harness**: provider-agnostic adapter for sending encoded payloads between two model APIs and measuring token use.
- **Benchmark CI gate**: workflow runs tests, re-syncs table, and fails on regressions.

## New docs

- `FUTURES.md`: message passing alternatives (shared state, blackboard, superposition).
- `PHILOSOPHY.md`: compression manifesto and moral argument for machine-native communication.

## Commands

```bash
python -m unittest
python -m logorrhythm.cli --benchmark
python -m logorrhythm.cli --v003-dashboard
python -m logorrhythm.cli --sync-benchmark-table
```

## License

Licensed under the Apache License, Version 2.0.
See the LICENSE file for details.
