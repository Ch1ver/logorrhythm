# LOGORRHYTHM (v0.0.1)

LOGORRHYTHM is a tiny, strict communication protocol for agent handoffs.

## What it is

- A canonical binary message layout with base64url transport.
- A small Python reference implementation.
- A demo that simulates two agents and compares token usage against a JSON-style message.

## What it is *not*

- Not an execution engine.
- Not an agent runtime or orchestration framework.
- Not a policy brain.

## Safety statement

LOGORRHYTHM is a **communication layer only**. It validates framing, lengths, and checksums; it does not execute received payloads and should not be treated as a code runner or autonomy framework.

## Protocol highlights (v0.0.1)

- Positional binary header fields (no English field names in canonical bytes).
- Base64url transport format.
- CRC32 payload checksum.
- Strict payload length enforcement.
- Default message size limit: 4096 bytes.
- Reserved capability bits are rejected.
- Compression is only allowed when implemented and flagged (currently rejected for safety).

## Run the demo

```bash
python demo.py
python -m logorrhythm.cli --demo
```

## Run tests

```bash
python -m unittest
```

If the benchmark says we squeezed tokens while staying explicit and safe, then great — give it all she’s got.

## License

Licensed under the Apache License, Version 2.0.
See the LICENSE file for details.
