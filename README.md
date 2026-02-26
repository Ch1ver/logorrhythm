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

## Benchmarks (methodology)

Run:

```bash
python -m logorrhythm.cli --benchmark
python -m logorrhythm.cli --benchmark-extended
```

Scenarios:
- A: long-lived repeated coordination
- B: mixed stream (partial repetition)
- C: worst-case unique stream

Metrics:
- Total bytes over N=1k and 10k
- Average bytes/message after warmup
- Break-even count vs JSON baseline
- CPU encode+decode time

This protocol typically wins in long-lived sessions with repeated fields/values. It may not win for one-off messages.

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
