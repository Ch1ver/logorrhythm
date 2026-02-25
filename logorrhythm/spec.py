"""Protocol constants for the stable wire format used by LOGORRHYTHM v0.0.5.

Package versions can evolve independently from protocol wire versions.
The package remains v0.0.5 while protocol v1 (legacy compact payload)
and protocol v2 (agent-capable envelope) can coexist.
"""

from __future__ import annotations

import enum

PROTOCOL_VERSION_LEGACY = 1
PROTOCOL_VERSION = 2
MAX_MESSAGE_BYTES = 4096

# 1-byte flags field
FLAG_COMPRESSED = 0b0000_0001
FLAG_SIGNED = 0b0000_0010

# 2-byte capability bitmask (uint16)
CAP_TEXT = 0b0000_0000_0000_0001
CAP_BINARY = 0b0000_0000_0000_0010
CAP_ROUTING = 0b0000_0000_0000_0100
CAP_SIGNED = 0b0000_0000_0000_1000
CAP_STREAMING = 0b0000_0000_0001_0000
CAP_SECURE_ENVELOPE = 0b0000_0000_0010_0000
CAP_ADAPTIVE_ALIASING = 0b0000_0000_0100_0000
CAP_HEARTBEAT = 0b0000_0000_1000_0000
CAP_TRANSPORT_WS = 0b0000_0001_0000_0000
ALLOWED_CAPABILITY_BITS = (
    CAP_TEXT
    | CAP_BINARY
    | CAP_ROUTING
    | CAP_SIGNED
    | CAP_STREAMING
    | CAP_SECURE_ENVELOPE
    | CAP_ADAPTIVE_ALIASING
    | CAP_HEARTBEAT
    | CAP_TRANSPORT_WS
)


class MessageType(enum.IntEnum):
    """Message type registry."""

    AGENT = 1


class AgentCode(enum.IntEnum):
    """Compact single-byte agent identifiers (legacy v1 payloads)."""

    A1 = 1
    A2 = 2


class InstructionCode(enum.IntEnum):
    """Legacy compact instruction identifiers."""

    HANDOFF = 0x01
    COMPLETE = 0x02
    QUERY = 0x03
    ACKNOWLEDGE = 0x04
    ERROR = 0x05


class InstructionType(str, enum.Enum):
    """String instruction registry for v2 envelopes."""

    HANDOFF = "HANDOFF"
    COMPLETE = "COMPLETE"
    QUERY = "QUERY"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    ERROR = "ERROR"
    WHOAMI = "WHOAMI"
    CAPABILITIES = "CAPABILITIES"
    HEARTBEAT = "HEARTBEAT"


# v1 Header layout: version:u8, msg_type:u8, flags:u8, capabilities:u16, payload_len:u16, crc32:u32
HEADER_SIZE = 1 + 1 + 1 + 2 + 2 + 4

# v2 Header layout: version:u8, msg_type:u8, flags:u8, capabilities:u16, payload_len:u16, crc32:u32
# same framing; payload structure differs.
HEADER_V2_SIZE = HEADER_SIZE

# v1 payload minimum: src:u8, dst:u8, instruction:u8
PAYLOAD_MIN_SIZE = 3
