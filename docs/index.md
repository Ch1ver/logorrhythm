# LOGORRHYTHM

Logorrhythm is a compact machine-native protocol for agent-to-agent communication.
It reduces message bytes, improves throughput, and lowers end-to-end latency in swarm workloads.
v0.0.4 adds adaptive compression, streaming, topology primitives, and fault-tolerant checkpoints.

## Quickstart

```python
from logorrhythm import send, receive
wire = send(task="summarize latest checkpoint")
print(receive(wire))
```

## Benchmarks

![Byte reduction trend](../benchmarks/graphs/byte_reduction_line.png)
![Throughput gain by scale](../benchmarks/graphs/throughput_scale_bar.png)
![Latency distribution p50/p95](../benchmarks/graphs/latency_distribution.png)

- Full spec: [SPEC.md](../SPEC.md)
