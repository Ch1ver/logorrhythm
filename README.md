# LOGORRHYTHM (v0.0.2)

LOGORRHYTHM is a two-layer protocol and execution language for AI-agent speed.

## Vision

LOGORRHYTHM is not a library. It is infrastructure for the agent era. When AI systems are running 120-day human workloads in 48 hours, they cannot afford to communicate in human-shaped formats. LOGORRHYTHM strips ceremony and ships pure signal: compact wire framing for inter-agent transport (Layer 1) and a compressed execution language for machine-native reasoning (Layer 2).

## Layer 1 status (wire protocol)

- Canonical binary header with positional fields.
- Base64url transport for tool-safe message exchange.
- CRC32 payload checksum and strict payload length enforcement.
- Default message size limit: 4096 bytes.
- Compact payload layout with no English field names:
  - `src:u8` (agent code)
  - `dst:u8` (agent code)
  - `instruction:u8` (opcode)
  - `task:utf8` (semantic content only)

### Instruction byte codes

- `0x01` HANDOFF
- `0x02` COMPLETE
- `0x03` QUERY
- `0x04` ACKNOWLEDGE
- `0x05` ERROR

## Layer 2 status (execution language)

v0.0.2 introduces a first compressed primitive sketch with 10 operations:

- `R` retrieve
- `S` store
- `C` compare
- `B` branch
- `L` loop
- `K` call
- `N` return
- `T` transform
- `F` filter
- `E` emit

See `SPEC.md` for formal encoding and `ROADMAP.md` for progression.

## Run the demo

```bash
python demo.py
python -m logorrhythm.cli --demo
```

The demo includes proxy benchmarks (char/byte/word) and optional `tiktoken` token counts when available.

## Run tests

```bash
python -m unittest
```

## License

Licensed under the Apache License, Version 2.0.
See the LICENSE file for details.
