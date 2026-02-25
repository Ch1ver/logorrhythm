"""Canonical binary encoding, transport helpers, and v2 agent envelope support."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import struct
import uuid
from dataclasses import dataclass

from .exceptions import DecodingError, EncodingError
from .spec import (
    ALLOWED_CAPABILITY_BITS,
    FLAG_COMPRESSED,
    FLAG_SIGNED,
    MAX_MESSAGE_BYTES,
    PAYLOAD_MIN_SIZE,
    AgentCode,
    InstructionCode,
    MessageType,
    PROTOCOL_VERSION,
    PROTOCOL_VERSION_LEGACY,
)

_HEADER_STRUCT = struct.Struct(">BBHHI")
_LEGACY_HEADER_STRUCT = struct.Struct(">BBBHHI")
_NONCE_STRUCT = struct.Struct(">Q")
_U16_STRUCT = struct.Struct(">H")
_CONTROL_TYPE_MASK = 0x0F
_CONTROL_FLAGS_SHIFT = 4
_SUPPORTED_FLAG_BITS = FLAG_COMPRESSED | FLAG_SIGNED
_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")


@dataclass(frozen=True)
class CompactPayload:
    src: AgentCode
    dst: AgentCode
    instruction: InstructionCode
    task: str


@dataclass(frozen=True)
class AgentEnvelopeV2:
    source_id: str
    destination_id: str
    instruction: str
    task: str
    correlation_id: str
    nonce: int
    signature: str


@dataclass(frozen=True)
class DecodedMessage:
    _buffer: memoryview
    version: int
    _message_type_raw: int
    flags: int
    capabilities: int
    payload_length: int

    @property
    def message_type(self) -> MessageType:
        return MessageType(self._message_type_raw)

    @property
    def payload(self) -> bytes:
        return self._buffer.tobytes()

    @property
    def payload_view(self) -> memoryview:
        return self._buffer

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "message_type": self.message_type.name,
            "flags": self.flags,
            "capabilities": self.capabilities,
            "payload_length": self.payload_length,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class SecurityConfig:
    shared_secret: bytes = b""
    secure_mode: bool = False


class ReplayNonceStore:
    """In-memory replay protector with deterministic behavior for testable decode."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, int]] = set()

    def check_and_mark(self, source_id: str, nonce: int) -> bool:
        key = (source_id, nonce)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


_DEFAULT_NONCE_STORE = ReplayNonceStore()


def encode_compact_payload(*, src: AgentCode, dst: AgentCode, instruction: InstructionCode, task: str) -> bytes:
    """Encode legacy compact payload: src:u8,dst:u8,instruction:u8,task:utf8."""
    if not isinstance(src, AgentCode):
        raise EncodingError("src must be an AgentCode")
    if not isinstance(dst, AgentCode):
        raise EncodingError("dst must be an AgentCode")
    if not isinstance(instruction, InstructionCode):
        raise EncodingError("instruction must be an InstructionCode")
    if not isinstance(task, str):
        raise EncodingError("task must be a UTF-8 string")
    return bytes((int(src), int(dst), int(instruction))) + task.encode("utf-8")


def _validate_agent_id(agent_id: str, field_name: str) -> None:
    if not isinstance(agent_id, str) or not agent_id:
        raise EncodingError(f"{field_name} must be a non-empty UTF-8 string")
    if not _AGENT_ID_RE.match(agent_id):
        raise EncodingError(f"malformed ID in {field_name}")


def _pack_sized_text(value: str, field_name: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) > 255:
        raise EncodingError(f"{field_name} exceeds 255 bytes")
    return bytes((len(raw),)) + raw


def _compute_hmac(*, data: bytes, shared_secret: bytes) -> str:
    return hmac.new(shared_secret, data, hashlib.sha256).hexdigest()


def encode_agent_payload_v2(
    *,
    source_id: str,
    destination_id: str,
    instruction: str,
    task: str,
    correlation_id: str | None = None,
    nonce: int | None = None,
    shared_secret: bytes = b"",
    secure_mode: bool = False,
) -> bytes:
    """Encode v2 agent payload with string addressing, correlation, and optional HMAC."""
    _validate_agent_id(source_id, "source_id")
    _validate_agent_id(destination_id, "destination_id")
    if not destination_id:
        raise EncodingError("missing destination")
    if not isinstance(task, str):
        raise EncodingError("task must be a UTF-8 string")
    if not isinstance(instruction, str) or not instruction:
        raise EncodingError("instruction must be a non-empty string")

    cid = correlation_id or str(uuid.uuid4())
    try:
        uuid.UUID(cid, version=4)
    except ValueError as exc:
        raise EncodingError("correlation_id must be UUID4") from exc

    msg_nonce = (uuid.uuid4().int & ((1 << 64) - 1)) if nonce is None else int(nonce)
    if msg_nonce < 0:
        raise EncodingError("nonce must be non-negative")

    task_bytes = task.encode("utf-8")
    if len(task_bytes) > 0xFFFF:
        raise EncodingError("task exceeds 65535 bytes")

    core = b"".join(
        (
            _pack_sized_text(source_id, "source_id"),
            _pack_sized_text(destination_id, "destination_id"),
            _pack_sized_text(instruction, "instruction"),
            _pack_sized_text(cid, "correlation_id"),
            _NONCE_STRUCT.pack(msg_nonce),
            _U16_STRUCT.pack(len(task_bytes)),
            task_bytes,
        )
    )

    signature = ""
    if secure_mode:
        if not shared_secret:
            raise EncodingError("secure_mode requires shared_secret")
        signature = _compute_hmac(data=core, shared_secret=shared_secret)

    sig_bytes = signature.encode("ascii")
    if len(sig_bytes) > 255:
        raise EncodingError("signature too long")
    return core + bytes((len(sig_bytes),)) + sig_bytes


def decode_compact_payload(payload: bytes) -> CompactPayload:
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


def _decode_sized_text(payload: bytes, offset: int, label: str) -> tuple[str, int]:
    if offset >= len(payload):
        raise DecodingError(f"invalid length for {label}")
    size = payload[offset]
    offset += 1
    end = offset + size
    if end > len(payload):
        raise DecodingError(f"invalid length for {label}")
    try:
        value = payload[offset:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DecodingError(f"malformed ID in {label}") from exc
    return value, end


def decode_agent_payload_v2(
    payload: bytes,
    *,
    security: SecurityConfig | None = None,
    nonce_store: ReplayNonceStore | None = None,
) -> AgentEnvelopeV2:
    """Decode and validate v2 agent payload."""
    security = security or SecurityConfig()
    nonce_store = nonce_store or _DEFAULT_NONCE_STORE

    offset = 0
    source_id, offset = _decode_sized_text(payload, offset, "source_id")
    destination_id, offset = _decode_sized_text(payload, offset, "destination_id")
    instruction, offset = _decode_sized_text(payload, offset, "instruction")
    correlation_id, offset = _decode_sized_text(payload, offset, "correlation_id")

    if not destination_id:
        raise DecodingError("missing destination")
    if not _AGENT_ID_RE.match(source_id):
        raise DecodingError("malformed ID in source_id")
    if not _AGENT_ID_RE.match(destination_id):
        raise DecodingError("malformed ID in destination_id")

    try:
        uuid.UUID(correlation_id, version=4)
    except ValueError as exc:
        raise DecodingError("missing correlation_id") from exc

    if offset + 8 + 2 > len(payload):
        raise DecodingError("Payload too short for nonce/task")

    nonce = _NONCE_STRUCT.unpack(payload[offset : offset + 8])[0]
    offset += 8

    task_len = _U16_STRUCT.unpack(payload[offset : offset + 2])[0]
    offset += 2
    if offset + task_len + 1 > len(payload):
        raise DecodingError("invalid length for task")

    task_bytes = payload[offset : offset + task_len]
    offset += task_len
    try:
        task = task_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DecodingError("task is not valid UTF-8") from exc

    sig_len = payload[offset]
    offset += 1
    if offset + sig_len != len(payload):
        raise DecodingError("invalid length for signature")
    signature = payload[offset : offset + sig_len].decode("ascii")

    signed_region = payload[: offset - 1]

    if security.secure_mode:
        if not signature:
            raise DecodingError("missing signature")
        expected = _compute_hmac(data=signed_region, shared_secret=security.shared_secret)
        if not hmac.compare_digest(signature, expected):
            raise DecodingError("invalid signature")

    if not nonce_store.check_and_mark(source_id, nonce):
        raise DecodingError("replayed nonce")

    return AgentEnvelopeV2(
        source_id=source_id,
        destination_id=destination_id,
        instruction=instruction,
        task=task,
        correlation_id=correlation_id,
        nonce=nonce,
        signature=signature,
    )


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
    version: int = PROTOCOL_VERSION_LEGACY,
    max_message_bytes: int = MAX_MESSAGE_BYTES,
    transport_base64: bool = False,
) -> bytes | str:
    if version not in (PROTOCOL_VERSION_LEGACY, PROTOCOL_VERSION):
        raise EncodingError(f"Unsupported protocol version for encoder: {version}")
    if capabilities & ~ALLOWED_CAPABILITY_BITS:
        raise EncodingError("Reserved capability bits must be zero")
    if flags & ~_SUPPORTED_FLAG_BITS:
        raise EncodingError("Reserved flag bits must be zero")
    payload = bytes(payload)
    if flags & FLAG_COMPRESSED:
        raise EncodingError("Compression flag is set but compression is not implemented")
    if len(payload) > 0xFFFF:
        raise EncodingError("Payload too large for length field")
    crc32 = binascii.crc32(payload) & 0xFFFFFFFF
    if transport_base64:
        header = _LEGACY_HEADER_STRUCT.pack(version, int(message_type), flags, capabilities, len(payload), crc32)
    else:
        control = ((flags & 0x0F) << _CONTROL_FLAGS_SHIFT) | (int(message_type) & _CONTROL_TYPE_MASK)
        header = _HEADER_STRUCT.pack(version, control, capabilities, len(payload), crc32)
    msg = header + payload
    if len(msg) > max_message_bytes:
        raise EncodingError("Encoded message exceeds max_message_bytes")
    if transport_base64:
        return _to_base64url(msg)
    return msg


def decode_message(encoded: bytes | str, *, max_message_bytes: int = MAX_MESSAGE_BYTES, security: SecurityConfig | None = None, nonce_store: ReplayNonceStore | None = None) -> DecodedMessage:
    if isinstance(encoded, str):
        max_encoded_chars = (4 * max_message_bytes + 2) // 3
        if len(encoded) > max_encoded_chars:
            raise DecodingError("Encoded transport exceeds max_message_bytes")
        message = _from_base64url(encoded)
        if len(message) < _LEGACY_HEADER_STRUCT.size:
            raise DecodingError("Message too short for header")
        version, msg_type_raw, flags, capabilities, payload_length, checksum = _LEGACY_HEADER_STRUCT.unpack(
            message[: _LEGACY_HEADER_STRUCT.size]
        )
        header_size = _LEGACY_HEADER_STRUCT.size
    else:
        message = bytes(encoded)
        if len(message) < _HEADER_STRUCT.size:
            raise DecodingError("Message too short for header")
        version, control, capabilities, payload_length, checksum = _HEADER_STRUCT.unpack(message[: _HEADER_STRUCT.size])
        msg_type_raw = control & _CONTROL_TYPE_MASK
        flags = (control >> _CONTROL_FLAGS_SHIFT) & 0x0F
        header_size = _HEADER_STRUCT.size

    if len(message) > max_message_bytes:
        raise DecodingError("Message exceeds max_message_bytes")
    if version not in (PROTOCOL_VERSION_LEGACY, PROTOCOL_VERSION):
        raise DecodingError(f"Unsupported protocol version: {version}")
    if capabilities & ~ALLOWED_CAPABILITY_BITS:
        raise DecodingError("Reserved capability bits must be zero")
    if flags & ~_SUPPORTED_FLAG_BITS:
        raise DecodingError("Reserved flag bits must be zero")
    if flags & FLAG_COMPRESSED:
        raise DecodingError("Compressed messages are not supported")

    payload = memoryview(message)[header_size:]
    if len(payload) != payload_length:
        raise DecodingError("payload_length mismatch")
    if (binascii.crc32(payload) & 0xFFFFFFFF) != checksum:
        raise DecodingError("CRC32 checksum mismatch")
    if msg_type_raw not in {int(mt) for mt in MessageType}:
        raise DecodingError(f"Unknown message type: {msg_type_raw}")

    if MessageType(msg_type_raw) is MessageType.AGENT:
        if version == PROTOCOL_VERSION_LEGACY:
            decode_compact_payload(payload.tobytes())
        else:
            decode_agent_payload_v2(payload.tobytes(), security=security, nonce_store=nonce_store)

    return DecodedMessage(payload, version, msg_type_raw, flags, capabilities, payload_length)


def render_message_human(decoded: DecodedMessage, *, security: SecurityConfig | None = None) -> str:
    if decoded.version == PROTOCOL_VERSION_LEGACY:
        compact = decode_compact_payload(decoded.payload)
        body = {"src": compact.src.name, "dst": compact.dst.name, "instruction": compact.instruction.name, "task": compact.task}
    else:
        agent = decode_agent_payload_v2(decoded.payload, security=security, nonce_store=ReplayNonceStore())
        body = {
            "source_id": agent.source_id,
            "destination_id": agent.destination_id,
            "instruction": agent.instruction,
            "task": agent.task,
            "correlation_id": agent.correlation_id,
            "nonce": agent.nonce,
            "signature_present": bool(agent.signature),
        }
    return json.dumps({"version": decoded.version, "message_type": decoded.message_type.name, "flags": decoded.flags, "capabilities": decoded.capabilities, "payload_length": decoded.payload_length, "payload": body}, indent=2, sort_keys=True)
