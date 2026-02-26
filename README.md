# LOGORRHYTHM + LOOM

## 1) What this is
LOGORRHYTHM is a token-efficient inter-agent communication protocol built around negotiated schema + opcode sessions. LOOM is the autonomous orchestrator built on top of it: give it a brief, let the agents run, and come back to artifacts and a report.

## 2) Why it exists
Autonomous AI workflows get expensive fast because most agent-to-agent communication still looks like verbose human prose. Logorrhythm removes that overhead with compact session framing, schema fingerprinting, and opcode payloads instead of natural-language chatter. LOOM extends that into execution by coordinating build/test/benchmark/review/report loops so the human provides intent up front and reviews results at the end.

## 3) Benchmark table (measured values)
The values below are copied from the existing Captain's Reports (v0.0.2 / v0.0.3 era measurements on the recorded host).

| Source | Scenario | JSON bytes | Logorrhythm bytes | Savings | CPU |
|---|---|---:|---:|---:|---:|
| CAPTAINS_REPORT_V3 | Adversarial unique, N=10,000 | 1,880,000 | 1,240,041 | 34.04% | n/a |
| CAPTAINS_REPORT_V3 | Adversarial unique, N=100,000 | 18,800,000 | 12,400,041 | 34.04% | n/a |
| CAPTAINS_REPORT_V2 | Repeated stream, N=10,000 | 770,000 | 160,058 | 79.21% | 24.53 µs/msg |
| CAPTAINS_REPORT_V2 | Repeated stream, N=100,000 | 7,700,000 | 1,600,058 | 79.22% | 24.71 µs/msg |

Also recorded in V3: handshake total is 41 bytes (HELLO 3 + fingerprint 34 + mode switch 2 + ACKs), and at repeated N=100,000 this is only 0.0026% of session bytes.

## 4) Quick start

### Path A — Use Logorrhythm as a protocol
```python
from logorrhythm import Session, load_schema

schema = load_schema("examples/session_schema.json")
client = Session(schema=schema, role="client")
server = Session(schema=schema, role="server")

# negotiate once
out = client.initiate_handshake()
for frame in server.receive(out):
    for back in client.receive(frame):
        server.receive(back)

# then send compact opcode messages
wire = client.encode("TASK", {"id": 7, "cmd": "scan", "target": "node-0", "value": 99})
decoded = server.decode(wire)
print(decoded)
```

### Path B — Use LOOM to build autonomously
```bash
python -m loom.start --brief brief.md
```

Minimal `brief.md`:
```md
Project: HelloLOOM
Vision: Build a Python CLI that returns whether an input number is prime.
Success criteria: Tests pass, benchmark exceeds 10,000 checks/sec, README exists.
Constraints: Pure Python, no external dependencies, keep implementation concise.
```

## 5) Project structure
```text
logorrhythm/
  core/        # active protocol implementation
  legacy/      # archived pre-pivot implementation
loom/
  agents/      # builder/tester/benchmarker/critic/reporter workers
  start.py     # architect entry point (`python -m loom.start`)
legacy/        # historical project docs/spec notes
tests/         # protocol and benchmark verification
docs/          # benchmark artifacts/graphs
benchmarks/    # (generated/implicit via CLI benchmark commands)
```

## 6) Running benchmarks
```bash
python -m logorrhythm.cli --benchmark
python -m logorrhythm.cli --benchmark-extended
```

- `--benchmark` runs core scenarios for session-vs-JSON size and throughput summaries.
- `--benchmark-extended` runs the full validation matrix, structural/adaptive breakdown, adversarial unique stream, nested fairness checks, and CPU comparison.
- Good numbers currently look like: ~79% savings on repeated streams, ~34% savings even on adversarial unique streams, and handshake overhead that rapidly amortizes toward ~0% as N grows.

## 7) Roadmap
- **Now:** Logorrhythm session protocol is active; LOOM exists as a 6-agent orchestrator scaffold wired through opcode messaging.
- **v0.1.0:** stabilize LOOM execution/reporting loops and publish verified end-to-end runs with reproducible artifacts.
- **v1.0.0:** production-hardening (retries, richer task decomposition, stronger evaluation gates, robust observability).
- **Long-term:** protocol + orchestrator become a practical autonomous software factory loop, not just a protocol experiment.
