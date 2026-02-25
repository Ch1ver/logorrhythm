# LOGORRHYTHM SPECIFICATION — v0.0.6 package / protocol v1+v2

## Versioning model

- Package version is **0.0.6**.
- Wire protocol versions are independent:
  - `PROTOCOL_VERSION_LEGACY = 1` (compact v0.0.2-compatible payload)
  - `PROTOCOL_VERSION = 2` (agent-capable envelope)

## Transport model

- **Binary-first default:** `encode_message(...)` returns raw bytes.
- **Compatibility mode:** `encode_message(..., transport_base64=True)` returns base64url transport string.

## Header structure

### Binary-first header (compacted)

- `version: u8`
- `control: u8` (`message_type` low 4 bits + `flags` high 4 bits)
- `capabilities: u16`
- `payload_len: u16`
- `crc32: u32`
- `payload: bytes`

### Base64 compatibility header (legacy framing)

- `version: u8`
- `message_type: u8`
- `flags: u8`
- `capabilities: u16`
- `payload_len: u16`
- `crc32: u32`
- `payload: bytes`

## Payload models

### Protocol v1 (legacy)

- `src: u8`
- `dst: u8`
- `instruction: u8`
- `task: utf8 bytes`

### Protocol v2 (agent envelope)

- `source_id: len(u8)+bytes`
- `destination_id: len(u8)+bytes`
- `instruction: len(u8)+bytes`
- `correlation_id(UUID4): len(u8)+bytes`
- `nonce: u64`
- `task: len(u16)+bytes`
- `signature: len(u8)+hex(hmac_sha256)` (optional unless secure mode)

## Decode model

- Decode uses a zero-copy payload view (`memoryview`) on hot path.
- Explicit bytes materialization remains available via `DecodedMessage.payload`.

## Security model

- `secure_mode=False` by default.
- When enabled, sender signs payload core with HMAC SHA256, receiver verifies signature and nonce replay.

## Benchmark hygiene

- CLI benchmarks are explicit (`--benchmark`, `token-benchmark`).
- Test runs remain side-effect free (no README/graph mutation).
- Graph generation is deterministic and CI-safe.
