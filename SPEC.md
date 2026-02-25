# LOGORRHYTHM SPECIFICATION — v0.0.2

This document is the canonical protocol definition for LOGORRHYTHM Layer 1 and the first Layer 2 draft.

## 1. Scope

v0.0.2 defines:

1. Binary message framing (header + payload).
2. Compact payload encoding rules for agent-to-agent instructions.
3. Instruction code registry.
4. Validation and rejection conditions.
5. Layer 2 primitive opcode sketch.

## 2. Layer 1 Wire Envelope

### 2.1 Transport

- Canonical message bytes MUST be base64url encoded without `=` padding for transport.
- Decoders MUST accept missing padding and normalize internally.

### 2.2 Header Layout (11 bytes, big-endian)

| Byte Range | Field | Type | Meaning |
|---|---|---|---|
| `0` | `version` | `u8` | Protocol version. Current value: `1`. |
| `1` | `msg_type` | `u8` | Message type code. Current value: `1` (`AGENT`). |
| `2` | `flags` | `u8` | Feature flags bitfield. |
| `3..4` | `capabilities` | `u16` | Capability bitmask. |
| `5..6` | `payload_len` | `u16` | Payload size in bytes. |
| `7..10` | `crc32` | `u32` | CRC32 checksum over payload bytes only. |

### 2.3 Flags

- Bit `0` (`0x01`) = `COMPRESSED`.
- v0.0.2 encoder/decoder MUST reject messages where this bit is set.

### 2.4 Capability Bits

Allowed bits:

- `0x0001` TEXT
- `0x0002` BINARY
- `0x0004` ROUTING
- `0x0008` SIGNED

All other capability bits are reserved.

- Encoders MUST reject non-zero reserved bits.
- Decoders MUST reject non-zero reserved bits.

### 2.5 Length and Integrity

- `payload_len` MUST equal actual payload byte count exactly.
- `crc32` MUST match payload exactly.
- Default max total message size is `4096` bytes (header + payload).

## 3. Layer 1 Payload Encoding (Compact Positional)

v0.0.2 payload format is positional and contains no English field names.

### 3.1 Payload Layout

| Byte Range | Field | Type | Meaning |
|---|---|---|---|
| `0` | `src` | `u8` | Source agent code. |
| `1` | `dst` | `u8` | Destination agent code. |
| `2` | `instruction` | `u8` | Instruction code. |
| `3..N` | `task` | `utf8` bytes | Human-language semantic task content. |

Minimum payload size: `3` bytes.

### 3.2 Agent Registry (initial)

- `0x01` = `A1`
- `0x02` = `A2`

Unknown agent codes MUST be rejected by compliant decoders.

### 3.3 Instruction Registry

- `0x01` = `HANDOFF`
- `0x02` = `COMPLETE`
- `0x03` = `QUERY`
- `0x04` = `ACKNOWLEDGE`
- `0x05` = `ERROR`

Unknown instruction codes MUST be rejected by compliant decoders.

### 3.4 Compression Rule

The payload MUST NOT include named keys like `from`, `to`, `instruction`, `task`.

Permitted human-readable text is restricted to semantic `task` bytes only.

## 4. Canonical Validation Rules

A decoder MUST reject on any of the following:

1. Invalid base64url transport.
2. Message size > max allowed bytes.
3. Message shorter than 11-byte header.
4. Unsupported protocol version.
5. Reserved capability bits non-zero.
6. Compression flag set (unsupported in v0.0.2).
7. `payload_len` mismatch.
8. CRC32 mismatch.
9. Unknown message type.
10. Compact payload shorter than 3 bytes.
11. Unknown `src` or `dst` code.
12. Unknown instruction code.
13. Non-UTF-8 task bytes.

## 5. Explicitly Rejected Patterns

The following are out of spec for v0.0.2:

- JSON object payloads with English keys.
- String instruction names inside payload bytes.
- Messages with compression bit set.
- Reserved capability bits set.
- Payload text interpreted as executable code.

## 6. Layer 2 Execution Language (Draft)

Layer 2 is a compact internal instruction set for agent planning and execution exchange.

### 6.1 Primitive Opcode Set (10)

| Op | Meaning |
|---|---|
| `R` | retrieve |
| `S` | store |
| `C` | compare |
| `B` | branch |
| `L` | loop |
| `K` | call |
| `N` | return |
| `T` | transform |
| `F` | filter |
| `E` | emit |

### 6.2 Draft Form

- Instruction format: `<OP> <arg>`
- Space-separated program stream.
- Branch labels and symbols are implementation-defined in v0.0.2.

Example:

`R ctx:status T x:sum(ctx) C x>0 B 1->L_ok F x by:item>0 L i<3 K plan N S mem:last=x E out:x`

## 7. Compliance

An implementation is v0.0.2 compliant when:

- It emits and parses the header exactly as defined.
- It enforces all rejection conditions.
- It encodes payloads in compact positional form.
- It uses numeric instruction codes, not English instruction strings in payload.
