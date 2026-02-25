"""Shared demo flow for LOGORRHYTHM v0.0.2."""

from __future__ import annotations

import json

from .bus import AgentBus
from .encoding import (
    decode_compact_payload,
    decode_message,
    encode_compact_payload,
    encode_message,
    render_message_human,
)
from .spec import CAP_ROUTING, CAP_TEXT, AgentCode, InstructionCode, MessageType


LAYER2_SAMPLE = [
    "R ctx:status",  # retrieve
    "T x:sum(ctx)",  # transform
    "C x > 0",  # compare
    "B 1 -> L_ok",  # branch
    "F x by:item>0",  # filter
    "L i<3",  # loop
    "K plan",  # call
    "N",  # return
    "S mem:last=x",  # store
    "E out:x",  # emit
]


def _proxy_stats(text: str) -> tuple[int, int, int]:
    return len(text), len(text.encode("utf-8")), len(text.split())


def run_demo() -> None:
    bus = AgentBus()

    payload = encode_compact_payload(
        src=AgentCode.A1,
        dst=AgentCode.A2,
        instruction=InstructionCode.HANDOFF,
        task="Please summarize latest status and continue.",
    )

    encoded = encode_message(
        message_type=MessageType.AGENT,
        payload=payload,
        capabilities=CAP_TEXT | CAP_ROUTING,
    )

    bus.send("agent2", encoded)

    print("Canonical encoded message (base64url):")
    print(encoded)

    received = bus.receive("agent2")[0]
    decoded = decode_message(received)

    print("\nHuman-readable rendering (non-canonical):")
    print(render_message_human(decoded))

    compact = decode_compact_payload(decoded.payload)
    plain_json = json.dumps(
        {
            "from": "agent1",
            "to": "agent2",
            "instruction": "HANDOFF",
            "task": compact.task,
        },
        separators=(",", ":"),
        sort_keys=True,
    )

    print("\nBenchmark comparison (proxy metrics):")
    plain_chars, plain_bytes, plain_words = _proxy_stats(plain_json)
    canonical_chars, canonical_bytes, canonical_words = _proxy_stats(encoded)
    print(f"plain_json_chars: {plain_chars}")
    print(f"canonical_transport_chars: {canonical_chars}")
    print(f"char_reduction_percent: {((plain_chars - canonical_chars) / plain_chars) * 100.0:.2f}%")
    print(f"plain_json_bytes: {plain_bytes}")
    print(f"canonical_transport_bytes: {canonical_bytes}")
    print(f"byte_reduction_percent: {((plain_bytes - canonical_bytes) / plain_bytes) * 100.0:.2f}%")
    print(f"plain_json_words: {plain_words}")
    print(f"canonical_transport_words: {canonical_words}")
    print(f"word_reduction_percent: {((plain_words - canonical_words) / plain_words) * 100.0:.2f}%")

    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        plain_tokens = len(enc.encode(plain_json))
        canonical_tokens = len(enc.encode(encoded))
        print("\nToken benchmark (cl100k_base):")
        print(f"plain_json_tokens: {plain_tokens}")
        print(f"canonical_transport_tokens: {canonical_tokens}")
        print(
            f"token_reduction_percent: {((plain_tokens - canonical_tokens) / plain_tokens) * 100.0:.2f}%"
        )
    except Exception:
        print("\nToken benchmark (cl100k_base) unavailable; proxy metrics used.")

    layer2_program = " ".join(LAYER2_SAMPLE)
    python_equivalent = (
        "status = retrieve(ctx['status']); x = transform_sum(status); "
        "if x > 0:\n    filtered = [i for i in x if i > 0]\n"
        "    for i in range(3):\n        plan(filtered)\n"
        "store(mem, 'last', x); emit(x)"
    )
    l2_chars, l2_bytes, l2_words = _proxy_stats(layer2_program)
    py_chars, py_bytes, py_words = _proxy_stats(python_equivalent)

    print("\nLayer 2 draft snippet:")
    print(layer2_program)
    print("\nLayer 2 vs Python proxy delta:")
    print(f"layer2_chars: {l2_chars}, python_chars: {py_chars}")
    print(f"layer2_bytes: {l2_bytes}, python_bytes: {py_bytes}")
    print(f"layer2_words: {l2_words}, python_words: {py_words}")
