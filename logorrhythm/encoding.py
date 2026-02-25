"""Canonical binary encoding and base64url transport helpers."""

from __future__ import annotations

import base64
import binascii
import json
import struct
from dataclasses import dataclass

from .exceptions import DecodingError, EncodingError
from .spec import (
    ALLOWED_CAPABILITY_BITS,
    FLAG_COMPRESSED,
    HEADER_SIZE,
    MAX_MESSAGE_BYTES,
    PAYLOAD_MIN_SIZE,
    AgentCode,
    InstructionCode,
    MessageType,
    PROTOCOL_VERSION,
)

# version:u8, msg_type:u8, flags:u8, capabilities:u16, payload_len:u16, crc32:u32
_HEADER_FORMAT = ">BBBHHI"


@dataclass(frozen=True)
class CompactPayload:
    src: AgentCode
    dst: AgentCode
    instruction: InstructionCode
    task: str


@dataclass(frozen=True)
class DecodedMessage:
    version: int
    message_type: MessageType
    flags: int
    capabilities: int
    payload_length: int
    payload: bytes


def encode_compact_payload(*, src: AgentCode, dst: AgentCode, instruction: InstructionCode, task: str) -> bytes:
    """Encode positional compact payload: src:u8,dst:u8,instruction:u8,task:utf8."""
    if not isinstance(src, AgentCode):
        raise EncodingError("src must be an AgentCode")
    if not isinstance(dst, AgentCode):
        raise EncodingError("dst must be an AgentCode")
    if not isinstance(instruction, InstructionCode):
        raise EncodingError("instruction must be an InstructionCode")
    if not isinstance(task, str):
        raise EncodingError("task must be a UTF-8 string")
    task_bytes = task.encode("utf-8")
    return bytes((int(src), int(dst), int(instruction))) + task_bytes


def decode_compact_payload(payload: bytes) -> CompactPayload:
    """Decode compact payload into a typed view."""
    if len(payload) < PAYLOAD_MIN_SIZE:
        raise DecodingError("Payload too short for compact format")

    src_raw, dst_raw, instruction_raw = payload[0], payload[1], payload[2]
    task_bytes = payload[3:]

    try:
        src = AgentCode(src_raw)
    except ValueError as exc:
        raise DecodingError(f"Unknown source agent code: {src_raw}") from exc

    try:
        dst = AgentCode(dst_raw)
    except ValueError as exc:
        raise DecodingError(f"Unknown destination agent code: {dst_raw}") from exc

    try:
        instruction = InstructionCode(instruction_raw)
    except ValueError as exc:
        raise DecodingError(f"Unknown instruction code: {instruction_raw}") from exc

    try:
        task = task_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DecodingError("Task segment is not valid UTF-8") from exc

    return CompactPayload(src=src, dst=dst, instruction=instruction, task=task)


def _to_base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _from_base64url(text: str) -> bytes:
    padding = "=" * ((4 - (len(text) % 4)) % 4)
    try:
        return base64.b64decode((text + padding).encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error, UnicodeEncodeError) as exc:
        raise DecodingError("Invalid base64url transport") from exc


def encode_message(
    *,
    message_type: MessageType,
    payload: bytes,
    flags: int = 0,
    capabilities: int = 0,
    version: int = PROTOCOL_VERSION,
    max_message_bytes: int = MAX_MESSAGE_BYTES,
) -> str:
    """Encode a canonical binary message and return base64url transport text."""
    if version != PROTOCOL_VERSION:
        raise EncodingError(f"Unsupported protocol version for encoder: {version}")
    if not isinstance(payload, (bytes, bytearray)):
        raise EncodingError("Payload must be bytes")
    if capabilities & ~ALLOWED_CAPABILITY_BITS:
        raise EncodingError("Reserved capability bits must be zero")

    payload = bytes(payload)
    if flags & FLAG_COMPRESSED:
        raise EncodingError("Compression flag is set but compression is not implemented")

    payload_length = len(payload)
    if payload_length > 0xFFFF:
        raise EncodingError("Payload too large for v0.0.2 length field")

    crc32 = binascii.crc32(payload) & 0xFFFFFFFF
    header = struct.pack(
        _HEADER_FORMAT,
        version,
        int(message_type),
        flags,
        capabilities,
        payload_length,
        crc32,
    )
    message = header + payload
    if len(message) > max_message_bytes:
        raise EncodingError("Encoded message exceeds max_message_bytes")

    return _to_base64url(message)


def decode_message(encoded: str, *, max_message_bytes: int = MAX_MESSAGE_BYTES) -> DecodedMessage:
    """Decode base64url text into a validated canonical message."""
    message = _from_base64url(encoded)

    if len(message) > max_message_bytes:
        raise DecodingError("Message exceeds max_message_bytes")
    if len(message) < HEADER_SIZE:
        raise DecodingError("Message too short for header")

    version, msg_type_raw, flags, capabilities, payload_length, checksum = struct.unpack(
        _HEADER_FORMAT, message[:HEADER_SIZE]
    )

    if version != PROTOCOL_VERSION:
        raise DecodingError(f"Unsupported protocol version: {version}")
    if capabilities & ~ALLOWED_CAPABILITY_BITS:
        raise DecodingError("Reserved capability bits must be zero")
    if flags & FLAG_COMPRESSED:
        raise DecodingError("Compressed messages are not supported in v0.0.2")

    payload = message[HEADER_SIZE:]
    if len(payload) != payload_length:
        raise DecodingError("payload_length mismatch")

    computed = binascii.crc32(payload) & 0xFFFFFFFF
    if computed != checksum:
        raise DecodingError("CRC32 checksum mismatch")

    try:
        message_type = MessageType(msg_type_raw)
    except ValueError as exc:
        raise DecodingError(f"Unknown message type: {msg_type_raw}") from exc

    return DecodedMessage(
        version=version,
        message_type=message_type,
        flags=flags,
        capabilities=capabilities,
        payload_length=payload_length,
        payload=payload,
    )


def render_message_human(decoded: DecodedMessage) -> str:
    """Non-canonical rendering for logs/debugging."""
    compact = decode_compact_payload(decoded.payload)
    return json.dumps(
        {
            "version": decoded.version,
            "message_type": decoded.message_type.name,
            "flags": decoded.flags,
            "capabilities": decoded.capabilities,
            "payload_length": decoded.payload_length,
            "payload": {
                "src": compact.src.name,
                "dst": compact.dst.name,
                "instruction": compact.instruction.name,
                "task": compact.task,
            },
        },
        indent=2,
        sort_keys=True,
    )
