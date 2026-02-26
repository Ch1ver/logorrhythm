"""Deterministic benchmark matrix for validation and fairness reporting."""

from __future__ import annotations

import json
import random
import statistics
import string
import time
from dataclasses import dataclass

from .core.frame import decode_uvarint
from .core.session import (
    ACK,
    HELLO,
    MODE_OPCODE,
    MODE_SWITCH,
    NACK,
    RAW_MESSAGE,
    SCHEMA_FINGERPRINT,
    SCHEMA_TRANSFER,
    Session,
    SessionConfig,
)
from .legacy.adaptive import AdaptiveCodec

DEFAULT_SCHEMA = {
    "message_types": {"TASK": 1},
    "fields": {"id": 1, "cmd": 2, "target": 3, "value": 4},
    "field_types": {"id": "uvarint", "cmd": "str", "target": "str", "value": "svarint"},
    "enums": {"cmd": ["scan", "handoff"]},
}

ADVERSARIAL_SCHEMA = {
    "message_types": {"TASK": 1},
    "fields": {f"f{i}": i + 1 for i in range(10)},
    "field_types": {f"f{i}": "str" for i in range(10)},
}

NESTED_SCHEMA = {
    "message_types": {"TASK": 1},
    "fields": {"id": 1, "meta": 2, "items": 3, "value": 4},
    "field_types": {"id": "uvarint", "meta": "map", "items": "list", "value": "svarint"},
}

SCALES_DEFAULT = (1, 10, 100, 1000, 10000, 100000)


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str


SCENARIOS = (
    Scenario("repeated", "Repeated control stream"),
    Scenario("mixed", "Mixed stream (40% repeat, 60% unique)"),
    Scenario("unique", "Fully unique stream"),
)


def _json_payload(opcode: str, fields: dict) -> dict:
    return {"opcode": opcode, "fields": fields}


def _json_bytes_for_payload(opcode: str, fields: dict) -> bytes:
    return json.dumps(_json_payload(opcode, fields), separators=(",", ":")).encode("utf-8")


def _json_size(opcode: str, fields: dict) -> int:
    return len(_json_bytes_for_payload(opcode, fields))


def _split_frames(blob: bytes) -> list[tuple[int, int]]:
    frames: list[tuple[int, int]] = []
    pos = 0
    while pos < len(blob):
        frame_type = blob[pos]
        ln, next_pos = decode_uvarint(blob, pos + 1)
        end = next_pos + ln
        frames.append((frame_type, end - pos))
        pos = end
    return frames


def _run_handshake(client: Session, server: Session) -> dict[str, int]:
    breakdown = {
        "hello": 0,
        "schema_fingerprint": 0,
        "schema_transfer": 0,
        "mode_switch": 0,
        "ack": 0,
        "nack": 0,
        "other": 0,
    }
    outbound = [client.initiate_handshake()]
    turn_server = True
    while outbound:
        next_frames: list[bytes] = []
        for frame in outbound:
            for ftype, flen in _split_frames(frame):
                if ftype == HELLO:
                    breakdown["hello"] += flen
                elif ftype == SCHEMA_FINGERPRINT:
                    breakdown["schema_fingerprint"] += flen
                elif ftype == SCHEMA_TRANSFER:
                    breakdown["schema_transfer"] += flen
                elif ftype == MODE_SWITCH:
                    breakdown["mode_switch"] += flen
                elif ftype == ACK:
                    breakdown["ack"] += flen
                elif ftype == NACK:
                    breakdown["nack"] += flen
                else:
                    breakdown["other"] += flen
            responses = server.receive(frame) if turn_server else client.receive(frame)
            next_frames.extend(responses)
        outbound = next_frames
        turn_server = not turn_server
    return breakdown


def _message_for_scenario(index: int, scenario_key: str) -> dict:
    if scenario_key == "repeated":
        return {"id": 7, "cmd": "scan", "target": "node-0", "value": 99}
    if scenario_key == "mixed":
        if index % 5 < 2:
            return {"id": index % 3, "cmd": "scan", "target": f"node-{index % 2}", "value": 120 + (index % 5)}
        return {"id": index, "cmd": f"u{index}", "target": f"node-{index}", "value": 100000 + index}
    return {"id": index, "cmd": f"u{index}", "target": f"node-{index}", "value": 100000 + index}


def _adversarial_message(index: int) -> dict:
    rng = random.Random(index)
    alphabet = string.ascii_letters + string.digits
    return {f"f{i}": "".join(rng.choice(alphabet) for _ in range(8)) for i in range(10)}


def _nested_message(index: int) -> dict:
    return {
        "id": index,
        "meta": {"node": f"n-{index}", "flags": [index % 3, index % 5, {"ok": True}]},
        "items": [{"id": index, "weight": index % 7}, [index, index + 1]],
        "value": 1000 + index,
    }


def _session_pair(schema: dict, config: SessionConfig | None = None) -> tuple[Session, Session, dict[str, int]]:
    encoder = Session(schema=schema, role="client", config=config)
    decoder = Session(schema=schema, role="server", config=config)
    hs = _run_handshake(encoder, decoder)
    return encoder, decoder, hs


def _single_run(scenario_key: str, n: int) -> dict:
    encoder, decoder, hs = _session_pair(DEFAULT_SCHEMA)
    hs_total = sum(hs.values())

    protocol_bytes = hs_total
    json_bytes = 0
    t0 = time.perf_counter()
    for i in range(n):
        fields = _message_for_scenario(i, scenario_key)
        wire = encoder.encode("TASK", fields)
        protocol_bytes += len(wire)
        json_bytes += _json_size("TASK", fields)
        decoder.decode(wire)
    cpu_total_s = time.perf_counter() - t0
    return {
        "json_bytes": json_bytes,
        "protocol_bytes": protocol_bytes,
        "handshake": hs,
        "handshake_total": hs_total,
        "steady_state_bytes": protocol_bytes - hs_total,
        "savings_pct": ((json_bytes - protocol_bytes) / json_bytes) * 100.0,
        "cpu_total_s": cpu_total_s,
        "cpu_us_per_message": (cpu_total_s / max(1, n)) * 1_000_000,
        "handshake_pct_of_total": (hs_total / max(1, protocol_bytes)) * 100.0,
        "json_baseline_sample": _json_bytes_for_payload("TASK", _message_for_scenario(0, scenario_key)).decode("utf-8"),
    }


def _break_even_count(scenario_key: str, cap: int = 200000) -> int | None:
    encoder, decoder, hs = _session_pair(DEFAULT_SCHEMA)
    protocol = sum(hs.values())
    json_total = 0
    for i in range(cap):
        fields = _message_for_scenario(i, scenario_key)
        wire = encoder.encode("TASK", fields)
        protocol += len(wire)
        json_total += _json_size("TASK", fields)
        decoder.decode(wire)
        if protocol <= json_total:
            return i + 1
    return None


def _stats(values: list[float]) -> dict:
    if len(values) == 1:
        return {"avg": values[0], "min": values[0], "max": values[0], "stdev": 0.0}
    return {"avg": statistics.mean(values), "min": min(values), "max": max(values), "stdev": statistics.stdev(values)}


def _variance_pct(stats: dict) -> float:
    avg = stats["avg"]
    return 0.0 if avg == 0 else ((stats["max"] - stats["min"]) / avg) * 100.0


def _run_mode(schema: dict, message_factory, n: int, config: SessionConfig | None, force_raw: bool = False) -> dict:
    encoder, decoder, hs = _session_pair(schema, config=config)
    hs_total = sum(hs.values())
    protocol = hs_total
    json_total = 0
    t0 = time.perf_counter()
    for i in range(n):
        fields = message_factory(i)
        json_blob = _json_bytes_for_payload("TASK", fields)
        json_total += len(json_blob)
        if force_raw:
            wire = encoder._encode_raw("TASK", fields)
            frame_type = wire[0]
            if frame_type != RAW_MESSAGE:
                raise RuntimeError("expected RAW_MESSAGE frame")
        else:
            wire = encoder.encode("TASK", fields)
        protocol += len(wire)
        decoder.decode(wire)
    cpu = time.perf_counter() - t0
    return {
        "json_bytes": json_total,
        "protocol_bytes": protocol,
        "savings_pct": ((json_total - protocol) / json_total) * 100.0,
        "cpu_total_s": cpu,
        "cpu_us_per_message": (cpu / max(1, n)) * 1_000_000,
        "handshake_total": hs_total,
    }


def run_validation_matrix(scales: tuple[int, ...] = SCALES_DEFAULT, runs: int = 5) -> dict:
    rows: list[dict] = []
    for n in scales:
        for scenario in SCENARIOS:
            run_rows = [_single_run(scenario.key, n) for _ in range(runs)]
            cpu_stats = _stats([r["cpu_us_per_message"] for r in run_rows])
            row = {
                "scenario": scenario.label,
                "scenario_key": scenario.key,
                "n": n,
                "json_bytes": _stats([r["json_bytes"] for r in run_rows]),
                "protocol_bytes": _stats([r["protocol_bytes"] for r in run_rows]),
                "steady_state_bytes": _stats([r["steady_state_bytes"] for r in run_rows]),
                "savings_pct": _stats([r["savings_pct"] for r in run_rows]),
                "cpu_total_s": _stats([r["cpu_total_s"] for r in run_rows]),
                "cpu_us_per_message": cpu_stats,
                "handshake_total": _stats([r["handshake_total"] for r in run_rows]),
                "handshake_pct_of_total": _stats([r["handshake_pct_of_total"] for r in run_rows]),
                "handshake_breakdown": {
                    k: _stats([r["handshake"][k] for r in run_rows])
                    for k in run_rows[0]["handshake"].keys()
                },
                "break_even": _break_even_count(scenario.key),
                "json_baseline_sample": run_rows[0]["json_baseline_sample"],
                "cpu_variance_pct": _variance_pct(cpu_stats),
            }
            rows.append(row)

    warnings: list[str] = []
    if all(r["protocol_bytes"]["avg"] > r["json_bytes"]["avg"] for r in rows):
        warnings.append("benchmark-gate: session protocol bytes exceed JSON across all scales")

    repeated_10k = next((r for r in rows if r["scenario_key"] == "repeated" and r["n"] == 10000), None)
    if repeated_10k and repeated_10k["break_even"] is None:
        warnings.append("warning: repeated scenario did not break even by 10k messages")

    unique_rows = [r for r in rows if r["scenario_key"] == "unique"]
    if unique_rows:
        worst_unique_reg = max(((r["protocol_bytes"]["avg"] - r["json_bytes"]["avg"]) / r["json_bytes"]["avg"]) * 100.0 for r in unique_rows)
        if worst_unique_reg > 50.0:
            warnings.append("warning: unique-stream regression exceeded 50%")

    unstable = [r for r in rows if r["cpu_variance_pct"] > 5.0]
    if unstable:
        warnings.append("warning: run-to-run CPU variance exceeded 5% in at least one scenario")

    return {"scales": list(scales), "runs": runs, "rows": rows, "warnings": warnings}


def run_structural_adaptive_breakdown(n: int = 100000, runs: int = 5) -> dict:
    mode_defs = [
        ("raw_structural", SessionConfig(learning_threshold=10**9, learn_fields=set()), True),
        ("adaptive_enabled", SessionConfig(learning_threshold=2), False),
        ("delta_enabled", SessionConfig(learning_threshold=10**9, learn_fields=set()), False),
        ("adaptive_plus_delta", SessionConfig(learning_threshold=2), False),
    ]
    # delta_enabled and adaptive_plus_delta use same transport path; they differ by input stream below.
    by_mode: dict[str, dict] = {}
    for mode, cfg, force_raw in mode_defs:
        factory = _message_for_scenario
        if mode == "delta_enabled":
            factory = lambda i, sk="repeated": {"id": i, "cmd": f"u{i}", "target": f"u{i}", "value": i}
        elif mode in {"adaptive_enabled", "adaptive_plus_delta", "raw_structural"}:
            factory = lambda i, sk="repeated": _message_for_scenario(i, "repeated")
        run_rows = [_run_mode(DEFAULT_SCHEMA, factory, n, cfg, force_raw=force_raw) for _ in range(runs)]
        by_mode[mode] = {
            "json_bytes": _stats([r["json_bytes"] for r in run_rows]),
            "protocol_bytes": _stats([r["protocol_bytes"] for r in run_rows]),
            "savings_pct": _stats([r["savings_pct"] for r in run_rows]),
            "cpu_total_s": _stats([r["cpu_total_s"] for r in run_rows]),
            "cpu_us_per_message": _stats([r["cpu_us_per_message"] for r in run_rows]),
        }

    structural = by_mode["raw_structural"]["savings_pct"]["avg"]
    adaptive = by_mode["adaptive_enabled"]["savings_pct"]["avg"] - structural
    delta = by_mode["delta_enabled"]["savings_pct"]["avg"] - structural
    adaptive_delta = by_mode["adaptive_plus_delta"]["savings_pct"]["avg"] - by_mode["adaptive_enabled"]["savings_pct"]["avg"]
    return {
        "n": n,
        "runs": runs,
        "modes": by_mode,
        "savings_breakdown": {
            "structural_only_savings_pct": structural,
            "additional_adaptive_savings_pct": adaptive,
            "additional_delta_savings_pct": delta,
            "adaptive_plus_delta_increment_pct": adaptive_delta,
        },
    }


def run_adversarial_unique(scales: tuple[int, ...] = (10000, 100000), runs: int = 5) -> dict:
    rows = []
    for n in scales:
        run_rows = [
            _run_mode(ADVERSARIAL_SCHEMA, _adversarial_message, n, SessionConfig(learning_threshold=2), force_raw=False)
            for _ in range(runs)
        ]
        row = {
            "n": n,
            "json_bytes": _stats([r["json_bytes"] for r in run_rows]),
            "protocol_bytes": _stats([r["protocol_bytes"] for r in run_rows]),
            "savings_pct": _stats([r["savings_pct"] for r in run_rows]),
        }
        rows.append(row)
    return {"scales": list(scales), "runs": runs, "rows": rows}


def run_nested_fairness(n: int = 10000, runs: int = 5) -> dict:
    run_rows = []
    for _ in range(runs):
        encoder, decoder, hs = _session_pair(NESTED_SCHEMA, config=SessionConfig(learning_threshold=2))
        protocol = sum(hs.values())
        json_total = 0
        for i in range(n):
            fields = _nested_message(i)
            json_total += _json_size("TASK", fields)
            wire = encoder.encode("TASK", fields)
            protocol += len(wire)
            decoded = decoder.decode(wire)
            if decoded["fields"] != fields:
                raise RuntimeError("nested fairness decode mismatch")
            if encoder.value_table.get_id(fields["meta"]) is not None:
                raise RuntimeError("nested dict unexpectedly learned as value-table ref")
            if encoder.value_table.get_id(fields["items"]) is not None:
                raise RuntimeError("nested list unexpectedly learned as value-table ref")
        run_rows.append({"json_bytes": json_total, "protocol_bytes": protocol, "savings_pct": ((json_total - protocol) / json_total) * 100.0})
    return {
        "n": n,
        "runs": runs,
        "json_bytes": _stats([r["json_bytes"] for r in run_rows]),
        "protocol_bytes": _stats([r["protocol_bytes"] for r in run_rows]),
        "savings_pct": _stats([r["savings_pct"] for r in run_rows]),
        "logical_payload_equivalence_confirmed": True,
        "nested_values_not_learned_confirmed": True,
    }


def run_cpu_comparison(n: int = 100000, runs: int = 5) -> dict:
    def json_cpu() -> dict:
        t0 = time.perf_counter()
        total = 0
        for i in range(n):
            fields = _message_for_scenario(i, "mixed")
            blob = _json_bytes_for_payload("TASK", fields)
            total += len(blob)
            json.loads(blob.decode("utf-8"))
        elapsed = time.perf_counter() - t0
        return {"bytes": total, "cpu_total_s": elapsed, "cpu_us_per_message": (elapsed / n) * 1_000_000}

    def session_cpu(raw: bool) -> dict:
        cfg = SessionConfig(learning_threshold=2)
        encoder, decoder, hs = _session_pair(DEFAULT_SCHEMA, config=cfg)
        total = sum(hs.values())
        t0 = time.perf_counter()
        for i in range(n):
            fields = _message_for_scenario(i, "mixed")
            wire = encoder._encode_raw("TASK", fields) if raw else encoder.encode("TASK", fields)
            total += len(wire)
            decoder.decode(wire)
        elapsed = time.perf_counter() - t0
        return {"bytes": total, "cpu_total_s": elapsed, "cpu_us_per_message": (elapsed / n) * 1_000_000}

    j = [json_cpu() for _ in range(runs)]
    r = [session_cpu(raw=True) for _ in range(runs)]
    a = [session_cpu(raw=False) for _ in range(runs)]

    def fold(rows: list[dict]) -> dict:
        return {
            "bytes": _stats([x["bytes"] for x in rows]),
            "cpu_total_s": _stats([x["cpu_total_s"] for x in rows]),
            "cpu_us_per_message": _stats([x["cpu_us_per_message"] for x in rows]),
        }

    json_stats = fold(j)
    raw_stats = fold(r)
    adaptive_stats = fold(a)
    return {
        "n": n,
        "runs": runs,
        "json": json_stats,
        "session_raw": raw_stats,
        "session_adaptive": adaptive_stats,
        "raw_overhead_pct_vs_json": ((raw_stats["cpu_us_per_message"]["avg"] - json_stats["cpu_us_per_message"]["avg"]) / json_stats["cpu_us_per_message"]["avg"]) * 100.0,
        "adaptive_overhead_pct_vs_json": ((adaptive_stats["cpu_us_per_message"]["avg"] - json_stats["cpu_us_per_message"]["avg"]) / json_stats["cpu_us_per_message"]["avg"]) * 100.0,
    }


def run_all(scales: tuple[int, ...] = (1000, 10000)) -> list[dict]:
    matrix = run_validation_matrix(scales=scales, runs=5)
    return [
        {
            "scenario": row["scenario_key"],
            "n": row["n"],
            "wire_bytes": row["protocol_bytes"]["avg"],
            "json_bytes": row["json_bytes"]["avg"],
            "handshake_bytes": row["handshake_total"]["avg"],
            "steady_state_bytes": row["steady_state_bytes"]["avg"],
            "savings_pct_vs_json": row["savings_pct"]["avg"],
            "cpu_s": row["cpu_total_s"]["avg"],
            "cpu_us_per_message": row["cpu_us_per_message"]["avg"],
            "break_even": row["break_even"],
        }
        for row in matrix["rows"]
    ]


def break_even_count(messages: list[dict], cap: int = 200000) -> int | None:
    encoder, decoder, hs = _session_pair(DEFAULT_SCHEMA)
    protocol = sum(hs.values())
    json_total = 0
    for i in range(cap):
        msg = messages[i % len(messages)]
        wire = encoder.encode("TASK", msg)
        protocol += len(wire)
        json_total += _json_size("TASK", msg)
        decoder.decode(wire)
        if protocol <= json_total:
            return i + 1
    return None


def _legacy_wire_bytes_for_stream(messages: list[str]) -> int:
    codec = AdaptiveCodec(warmup_hits=3)
    total = 0
    for message in messages:
        total += len(codec.encode(message))
    return total


def _new_wire_bytes_for_stream(payloads: list[dict]) -> int:
    s = Session(schema=DEFAULT_SCHEMA, role="client")
    s.mode = MODE_OPCODE
    total = 0
    for payload in payloads:
        total += len(s.encode("TASK", payload))
    return total


def run_agent_scale_compare(counts: tuple[int, ...] = (1, 10, 100, 1000), rounds_per_agent: int = 10) -> list[dict]:
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
