# LOGORRHYTHM

LOGORRHYTHM is now a **stateful session-negotiated opcode protocol for agent-to-agent communication**.

Human readability is not a wire requirement. Sessions negotiate a schema fingerprint, optionally transfer schema bytes, then switch to compact opcode mode.

## Core Model

1. HELLO + capability flags
2. SCHEMA_FINGERPRINT
3. ACK if known, otherwise NACK and SCHEMA_TRANSFER
4. ACK
5. MODE_SWITCH to `OPCODE_MODE`

In opcode mode, messages encode as compact binary frames with varints, field IDs, value references, and optional numeric deltas.

## Minimal API

```python
from logorrhythm import Session, load_schema

schema = load_schema("examples/session_schema.json")
client = Session(schema=schema, role="client")
server = Session(schema=schema, role="server")

# Handshake
out = client.initiate_handshake()
responses = server.receive(out)
for frame in responses:
    for back in client.receive(frame):
        server.receive(back)

# Opcode mode
wire = client.encode(opcode="TASK", fields={"id": 7, "cmd": "scan", "target": "x", "status": "ok"})
decoded = server.decode(wire)
```

## BENCHMARKS (Session Protocol Methodology)

Logorrhythm is a **stateful session protocol**. Results are measured over whole sessions, not single packets.

1. Savings depend on both message count and repetition density.
2. Handshake + schema negotiation cost is paid once, then amortized.
3. Unique-heavy streams can regress vs JSON.
4. Break-even point varies by schema shape, literal repetition, and field entropy.

| Transport Mode | Scope | Total Bytes (N messages) | Break-even | CPU µs/msg | Notes |
|---|---|---:|---:|---:|---|
| JSON baseline | Stateless | scenario-dependent | n/a | baseline | Human-readable baseline |
| Session RAW mode | Session | scenario-dependent | varies | host-dependent | No learning, structural compression only |
| Session OPCODE mode | Session | scenario-dependent | varies | host-dependent | Schema-negotiated compression |
| Session Adaptive mode | Long-lived | scenario-dependent | typically < X messages | host-dependent | Learns repeated literals |
| Worst-case unique | Session | may regress | n/a | host-dependent | Bounded regression expected |

**Measured values are host-dependent. Results shown in CAPTAINS_REPORT reflect test host only.**

```bash
python -m logorrhythm.cli --benchmark
python -m logorrhythm.cli --benchmark-extended
```

Scenarios:
- Repeated control stream
- Mixed stream (40% repeat, 60% unique)
- Fully unique stream

Metrics per scale (N = 1, 10, 100, 1k, 10k, 100k):
- total JSON bytes
- total session-protocol bytes (includes one-time handshake/schema cost)
- handshake overhead vs steady-state bytes
- savings percentage
- break-even message count
- encode+decode CPU total and CPU µs/msg
- avg/min/max/stdev across 3 runs

## Project Layout

- `logorrhythm/core/` active protocol implementation
- `logorrhythm/legacy/` archived pre-pivot modules
- `examples/session_schema.json` minimal schema

## Tests

```bash
python -m unittest
```


## Legacy vs Pivot comparison

To compare old adaptive control framing vs the new opcode session at scales used previously (1, 10, 100, 1000 agents):

```bash
python -m logorrhythm.cli --compare-legacy
```

This emits byte totals and ratios for ring-style coordination streams so you can evaluate if the pivot improved your target pattern.


The extended benchmark includes 100k-message runs so you can verify savings trend beyond 1k and inspect CPU cost per message against byte savings.
