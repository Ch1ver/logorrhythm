# Captain's Report — Pivot to Session Opcode Protocol (0.1.0)

## Summary

The project has been re-centered on stateful agent-to-agent sessions with schema negotiation and opcode compression.

## Current truth

- The active implementation is under `logorrhythm/core/`.
- Handshake flow now negotiates schema fingerprints and supports transfer-on-mismatch.
- Binary opcode mode includes value references, learning thresholds, and numeric delta encoding.
- If negotiation cannot complete, RAW mode provides safe fallback continuity.

## Legacy handling

Pre-pivot modules were moved under `logorrhythm/legacy/` to reduce confusion while preserving history.

## Benchmarks

Benchmarks now report scenario-driven measurements instead of static promises. Run `python -m logorrhythm.cli --benchmark` for A/B/C outputs on your host.


## Added regression check requested by review

A dedicated scale comparison path now exists for 1/10/100/1000-agent coordination streams:
`python -m logorrhythm.cli --compare-legacy`.
It reports new opcode wire bytes against legacy adaptive wire bytes with deltas and ratios.
