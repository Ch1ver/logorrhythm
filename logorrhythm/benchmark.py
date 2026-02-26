"""Session benchmark scenarios for opcode protocol + legacy comparison."""

from __future__ import annotations

import json
import time

from .core.session import MODE_OPCODE, Session
from .legacy.adaptive import AdaptiveCodec


DEFAULT_SCHEMA = {
    "message_types": {"TASK": 1},
    "fields": {"id": 1, "cmd": 2, "target": 3, "value": 4},
    "field_types": {"id": "uvarint", "cmd": "str", "target": "str", "value": "uvarint"},
    "enums": {
        "cmd": ["scan", "handoff"],
    },
}


def _json_size(msg: dict) -> int:
    return len(json.dumps(msg, separators=(",", ":")).encode("utf-8"))


def _warm_session(schema: dict) -> Session:
    s = Session(schema=schema, role="client")
    s.mode = MODE_OPCODE
    return s


def run_scenario(name: str, messages: list[dict], n: int) -> dict:
    a = _warm_session(DEFAULT_SCHEMA)
    b = _warm_session(DEFAULT_SCHEMA)
    total_wire = total_json = 0
    t0 = time.perf_counter()
    for i in range(n):
        msg = messages[i % len(messages)]
        wire = a.encode("TASK", msg)
        total_wire += len(wire)
        total_json += _json_size({"opcode": "TASK", "fields": msg})
        b.decode(wire)
    t1 = time.perf_counter()
    warm_start = min(100, n)
    warm_wire = 0
    for i in range(warm_start, n):
        msg = messages[i % len(messages)]
        warm_wire += len(a.encode("TASK", msg))
    avg_after_warm = warm_wire / max(1, (n - warm_start))
    return {
        "scenario": name,
        "n": n,
        "wire_bytes": total_wire,
        "json_bytes": total_json,
        "savings_pct_vs_json": ((total_json - total_wire) / total_json) * 100.0,
        "avg_after_warm": avg_after_warm,
        "cpu_s": t1 - t0,
        "cpu_us_per_message": ((t1 - t0) / n) * 1_000_000,
        "break_even": break_even_count(messages),
    }


def break_even_count(messages: list[dict], cap: int = 200000) -> int | None:
    a = _warm_session(DEFAULT_SCHEMA)
    wire = js = 0
    for i in range(cap):
        msg = messages[i % len(messages)]
        wire += len(a.encode("TASK", msg))
        js += _json_size({"opcode": "TASK", "fields": msg})
        if wire <= js:
            return i + 1
    return None


def run_all(scales: tuple[int, ...] = (1000, 10000)) -> list[dict]:
    repeated = [{"id": 7, "cmd": "scan", "target": "x", "value": 99}]
    mixed = [
        {"id": i % 10, "cmd": "scan", "target": f"node-{i%5}", "value": i % 100}
        for i in range(20)
    ]
    unique = [
        {"id": i, "cmd": f"u{i}", "target": f"t{i}", "value": i * 11}
        for i in range(200)
    ]
    results = []
    for n in scales:
        results.append(run_scenario("A_repeated", repeated, n))
        results.append(run_scenario("B_mixed", mixed, n))
        results.append(run_scenario("C_unique", unique, n))
    return results


def _legacy_wire_bytes_for_stream(messages: list[str]) -> int:
    codec = AdaptiveCodec(warmup_hits=3)
    total = 0
    for message in messages:
        total += len(codec.encode(message))
    return total


def _new_wire_bytes_for_stream(payloads: list[dict]) -> int:
    s = _warm_session(DEFAULT_SCHEMA)
    total = 0
    for payload in payloads:
        total += len(s.encode("TASK", payload))
    return total


def run_agent_scale_compare(counts: tuple[int, ...] = (1, 10, 100, 1000), rounds_per_agent: int = 10) -> list[dict]:
    """Compare legacy adaptive control-message bytes vs new opcode session bytes."""
    rows: list[dict] = []
    for agents in counts:
        payloads = []
        legacy_msgs = []
        for r in range(rounds_per_agent):
            for aid in range(agents):
                target = (aid + 1) % agents if agents > 1 else 0
                payload = {"id": aid, "cmd": "handoff", "target": f"a{target}", "value": r}
                payloads.append(payload)
                legacy_msgs.append(f"HANDOFF:a{aid}>a{target}:{r}")
        new_wire = _new_wire_bytes_for_stream(payloads)
        legacy_wire = _legacy_wire_bytes_for_stream(legacy_msgs)
        rows.append(
            {
                "agents": agents,
                "messages": len(payloads),
                "new_wire_bytes": new_wire,
                "legacy_wire_bytes": legacy_wire,
                "delta_bytes": new_wire - legacy_wire,
                "new_vs_legacy_ratio": (new_wire / legacy_wire) if legacy_wire else None,
            }
        )
    return rows
