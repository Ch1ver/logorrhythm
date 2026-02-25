"""LOGORRHYTHM v0.0.3 package."""

from .encoding import (
    CompactPayload,
    DecodedMessage,
    decode_compact_payload,
    decode_message,
    encode_compact_payload,
    encode_message,
    render_message_human,
)
from .spec import AgentCode, InstructionCode, MAX_MESSAGE_BYTES, MessageType, PROTOCOL_VERSION
from .v003 import build_v003_dashboard

__all__ = [
    "CompactPayload",
    "DecodedMessage",
    "decode_compact_payload",
    "decode_message",
    "encode_compact_payload",
    "encode_message",
    "render_message_human",
    "AgentCode",
    "InstructionCode",
    "MAX_MESSAGE_BYTES",
    "MessageType",
    "PROTOCOL_VERSION",
    "build_v003_dashboard",
    "sync_readme_benchmark_table",
]

from .benchmark_sync import sync_readme_benchmark_table
