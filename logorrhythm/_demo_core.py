"""Shared demo flow for LOGORRHYTHM v0.0.1."""

from __future__ import annotations

import json

from .bus import AgentBus
from .encoding import decode_message, encode_message, render_message_human
from .spec import CAP_ROUTING, CAP_TEXT, MessageType


def run_demo() -> None:
    bus = AgentBus()

    sender = "agent1"
    recipient = "agent2"
    payload_obj = {
        "from": sender,
        "to": recipient,
        "instruction": "HANDOFF",
        "task": "Please summarize the latest status and continue.",
    }
    payload_bytes = json.dumps(payload_obj, separators=(",", ":")).encode("utf-8")

    encoded = encode_message(
        message_type=MessageType.HANDOFF,
        payload=payload_bytes,
        capabilities=CAP_TEXT | CAP_ROUTING,
    )

    bus.send(recipient, encoded)

    print("Canonical encoded message (base64url):")
    print(encoded)

    received = bus.receive(recipient)[0]
    decoded = decode_message(received)

    print("\nHuman-readable rendering (non-canonical):")
    print(render_message_human(decoded))

    try:
        import tiktoken
    except ImportError:
        print("\nToken benchmark skipped (install tiktoken to enable).")
        return

    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        print(
            "\nToken benchmark skipped: cl100k_base unavailable (network/proxy). "
            "Install or allow download to enable."
        )
        return

    json_equivalent = json.dumps(
        {
            "version": decoded.version,
            "message_type": decoded.message_type.name,
            "flags": decoded.flags,
            "capabilities": decoded.capabilities,
            "payload": payload_obj,
            "checksum": "crc32",
        },
        separators=(",", ":"),
        sort_keys=True,
    )

    canonical_tokens = len(enc.encode(encoded))
    json_tokens = len(enc.encode(json_equivalent))
    reduction = ((json_tokens - canonical_tokens) / json_tokens * 100.0) if json_tokens else 0.0

    print("\nToken benchmark (cl100k_base):")
    print(f"canonical_base64url_tokens: {canonical_tokens}")
    print(f"json_equivalent_tokens: {json_tokens}")
    print(f"reduction_percent: {reduction:.2f}%")
