# LOGORRHYTHM SPECIFICATION — v0.0.3

> Versioning note: package releases (for example v0.0.5) can ship implementation and testing improvements without changing the wire protocol. The canonical wire protocol version remains `PROTOCOL_VERSION = 1` unless a breaking framing change is introduced.
## Layer 1

### Envelope
- Binary frame + base64url transport remains canonical.
- Header is unchanged from v0.0.2 for backward compatibility.

### Chunked transport extension
Large payloads can be split into chunk frames carrying:
- `transfer_id` (deterministic hash),
- `seq_id` (0-indexed),
- `total_chunks`,
- `payload`.

Reassembly MUST be deterministic: all chunk IDs present exactly once and ordered by `seq_id`.

### Addressing extension
Agent identity is now globally scoped:
`<region>/<node>/<model>/<shard>/<agent>`.

This supports 10,000+ agents across heterogeneous model providers and machine pools.

### Dead-agent detection
Heartbeat algorithm:
- Agent emits heartbeat at fixed interval `I`.
- Detector marks dead only after `grace_misses + 1` missed intervals.
- One missed heartbeat alone is not failure.

## Layer 2

v0.0.3 keeps the original 10 primitives and adds:
- `Q` confidence branch
- `P` parallel fan-out
- `J` parallel join
- `H` model handoff
- `W` working-memory scope
- `M` long-term-memory scope
- `Y` shared-swarm-memory scope

## Benchmark gate
README benchmark table is canonical release truth and is auto-synced by `--sync-benchmark-table`.
Releases are blocked when table values regress or drift from computed benchmarks.
