"""Minimal public API surface for pip consumers."""

from __future__ import annotations

from .encoding import decode_compact_payload, decode_message, encode_compact_payload, encode_message
from .spec import AgentCode, InstructionCode, MessageType


def encode(*, task: str, src: AgentCode = AgentCode.A1, dst: AgentCode = AgentCode.A2, instruction: InstructionCode = InstructionCode.HANDOFF) -> str:
    payload = encode_compact_payload(src=src, dst=dst, instruction=instruction, task=task)
    return encode_message(message_type=MessageType.AGENT, payload=payload)


def decode(encoded: str) -> str:
    message = decode_message(encoded)
    return decode_compact_payload(message.payload).task


def send(*, task: str) -> str:
    return encode(task=task)


def receive(encoded: str) -> str:
    return decode(encoded)
