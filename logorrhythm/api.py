"""Public API surface for legacy and agent-capable flows."""

from __future__ import annotations

import uuid

from .encoding import (
    ReplayNonceStore,
    SecurityConfig,
    decode_agent_payload_v2,
    decode_compact_payload,
    decode_message,
    encode_agent_payload_v2,
    encode_compact_payload,
    encode_message,
)
from .exceptions import DecodingError
from .spec import AgentCode, InstructionCode, MessageType, PROTOCOL_VERSION


def encode(*, task: str, src: str = "agent-A1", dst: str = "agent-A2", instruction: str = "HANDOFF", correlation_id: str | None = None, shared_secret: bytes = b"", secure_mode: bool = False) -> str:
    payload = encode_agent_payload_v2(
        source_id=src,
        destination_id=dst,
        instruction=instruction,
        task=task,
        correlation_id=correlation_id,
        shared_secret=shared_secret,
        secure_mode=secure_mode,
    )
    flags = 0
    if secure_mode:
        flags |= 0b10
    return encode_message(message_type=MessageType.AGENT, payload=payload, version=PROTOCOL_VERSION, flags=flags, transport_base64=True)


def decode(encoded: str, *, shared_secret: bytes = b"", secure_mode: bool = False) -> str:
    message = decode_message(encoded, security=SecurityConfig(shared_secret=shared_secret, secure_mode=secure_mode))
    if message.version == PROTOCOL_VERSION:
        return decode_agent_payload_v2(message.payload, security=SecurityConfig(shared_secret=shared_secret, secure_mode=secure_mode), nonce_store=ReplayNonceStore()).task
    return decode_compact_payload(message.payload).task


def send(*, task: str) -> str:
    return encode(task=task)


def receive(encoded: str) -> str:
    return decode(encoded)


def encode_legacy(*, task: str, src: AgentCode = AgentCode.A1, dst: AgentCode = AgentCode.A2, instruction: InstructionCode = InstructionCode.HANDOFF) -> str:
    payload = encode_compact_payload(src=src, dst=dst, instruction=instruction, task=task)
    return encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)


def ensure_response_correlation(request_correlation_id: str, response_correlation_id: str) -> None:
    try:
        request = uuid.UUID(request_correlation_id)
        response = uuid.UUID(response_correlation_id)
    except (ValueError, AttributeError, TypeError) as exc:
        raise DecodingError("correlation_id must be UUID4") from exc
    if request.version != 4 or response.version != 4:
        raise DecodingError("correlation_id must be UUID4")
    if request_correlation_id != response_correlation_id:
        raise DecodingError("mismatched correlation_id")
