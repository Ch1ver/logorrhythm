"""Protocol constants for the stable wire format used by LOGORRHYTHM v0.0.5.

Package versions can evolve independently from the protocol wire version.
The current package release is v0.0.5 while `PROTOCOL_VERSION = 1`
retains v0.0.2-compatible framing for backward compatibility.
"""

from __future__ import annotations

import enum

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 4096

# 1-byte flags field
FLAG_COMPRESSED = 0b0000_0001

# 2-byte capabilities bitmask (uint16)
CAP_TEXT = 0b0000_0000_0000_0001
CAP_BINARY = 0b0000_0000_0000_0010
CAP_ROUTING = 0b0000_0000_0000_0100
CAP_SIGNED = 0b0000_0000_0000_1000
ALLOWED_CAPABILITY_BITS = CAP_TEXT | CAP_BINARY | CAP_ROUTING | CAP_SIGNED


class MessageType(enum.IntEnum):
    """v0.0.2 message type registry."""

    AGENT = 1


class AgentCode(enum.IntEnum):
    """Compact single-byte agent identifiers."""

    A1 = 1
    A2 = 2


class InstructionCode(enum.IntEnum):
    """Compact single-byte instruction identifiers."""

    HANDOFF = 0x01
    COMPLETE = 0x02
    QUERY = 0x03
    ACKNOWLEDGE = 0x04
    ERROR = 0x05


# Header layout:
# version:u8, msg_type:u8, flags:u8, capabilities:u16, payload_len:u16, crc32:u32
HEADER_SIZE = 1 + 1 + 1 + 2 + 2 + 4

# Payload layout:
# src:u8, dst:u8, instruction:u8, task_utf8:bytes
PAYLOAD_MIN_SIZE = 3
