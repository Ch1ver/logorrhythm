"""Protocol specification constants for LOGORRHYTHM v0.0.1."""

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
    """v0.0.1 message type registry."""

    HANDOFF = 1


HEADER_SIZE = 1 + 1 + 1 + 2 + 2 + 4
