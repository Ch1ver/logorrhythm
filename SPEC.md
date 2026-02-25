# LOGORRHYTHM SPECIFICATION — v0.0.5 package / protocol v1+v2

## Versioning model

- Package version remains **0.0.5**.
- Wire protocol versions are independent:
  - `PROTOCOL_VERSION_LEGACY = 1` (compact v0.0.2-compatible payload)
  - `PROTOCOL_VERSION = 2` (agent-capable envelope)

## Header structure (shared framing)

Binary frame then base64url transport:

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

Length-prefixed UTF-8 strings and metadata:

- `source_id: len(u8)+bytes`
- `destination_id: len(u8)+bytes`
- `instruction: len(u8)+bytes`
- `correlation_id(UUID4): len(u8)+bytes`
- `nonce: u64`
- `task: len(u16)+bytes`
- `signature: len(u8)+hex(hmac_sha256)` (optional unless secure mode)

## Security model

- `secure_mode=False` by default to preserve benchmark path behavior.
- When secure mode is enabled:
  - sender signs `header+payload-core` with shared secret (HMAC SHA256),
  - receiver verifies signature,
  - missing or invalid signatures are rejected,
  - nonce replay is rejected through receiver-side nonce store.

## Correlation model

- `correlation_id` is auto-assigned UUID4 on message creation when omitted.
- Response handling must echo request correlation ID.
- Mismatches are rejected.

## Handshake and discovery

Supported instruction strings:

- `WHOAMI`
- `CAPABILITIES`
- `HEARTBEAT`

Flow:
1. Exchange `WHOAMI`.
2. Exchange `CAPABILITIES`.
3. Register peer in in-memory registry.
4. Periodically update `last_seen` via heartbeat.
5. Remove stale agents after timeout.

## Capability negotiation

Bitmask capabilities:

- `streaming`
- `secure_envelope`
- `adaptive_aliasing`
- `heartbeat`
- `transport_ws`

Negotiation result is the bitwise intersection of local/peer capabilities; unsupported features must fall back safely.

## Observer plane logging

JSON-lines event shape:

- `timestamp`
- `correlation_id`
- `source_id`
- `destination_id`
- `instruction`
- `payload_size_bytes`
- `total_size_bytes`
- `latency_ms`
- `status`
- `signature_verified`

## Benchmark hygiene

- Benchmark code path remains untouched (`benchmark_v001_vs_v002`).
- New security and envelope features are opt-in and disabled by default.
