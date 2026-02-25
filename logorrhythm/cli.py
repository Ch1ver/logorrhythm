"""CLI entrypoints for LOGORRHYTHM."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._demo_core import run_demo
from .benchmark import (
    benchmark_adaptive_repeated_exchange_percent,
    benchmark_decode_cpu_before_after,
    benchmark_encode_decode_throughput,
    benchmark_memory_allocations,
    benchmark_tokens,
    benchmark_v001_vs_v002,
)
from .benchmark_sync import sync_graph_artifacts, sync_readme_benchmark_table
from .encoding import decode_message, render_message_human
from .observer import emit_event
from .v003 import build_v003_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOGORRHYTHM command line interface")
    parser.add_argument("--demo", action="store_true", help="Run the v0.0.2 demo")
    parser.add_argument("--benchmark", action="store_true", help="Run transport and hot-path benchmarks")
    parser.add_argument("--v003-dashboard", action="store_true", help="Run the v0.0.3 scale simulation and print dashboard markdown")
    parser.add_argument("--sync-benchmark-table", action="store_true", help="Recompute benchmark table and write to README")
    parser.add_argument("--generate-graphs", action="store_true", help="Generate deterministic graph artifacts in docs/graphs")

    sub = parser.add_subparsers(dest="command")
    inspect_cmd = sub.add_parser("inspect", help="Inspect an encoded message")
    inspect_cmd.add_argument("encoded_message")

    tap_cmd = sub.add_parser("tap", help="Emit structured event logs")
    tap_cmd.add_argument("--ws", action="store_true", help="tap websocket events")

    replay_cmd = sub.add_parser("replay", help="Replay a JSON-lines log file")
    replay_cmd.add_argument("logfile")

    sub.add_parser("token-benchmark", help="Measure token cost across transports")
    return parser


def _print_token_table() -> None:
    report = benchmark_tokens(runs=5)
    print(f"Token benchmark report (avg over {report.runs} runs)")
    print("| Scenario | JSON | Base64 | Adaptive | Base64 Savings | Adaptive Savings |")
    print("|---|---:|---:|---:|---:|---:|")
    for s in report.scenarios:
        print(
            f"| {s.name} | {s.json_tokens} | {s.base64_tokens} | {s.adaptive_tokens} | "
            f"{s.base64_savings_percent:.2f}% | {s.adaptive_savings_percent:.2f}% |"
        )
    print(
        f"Averages: json={report.avg_json_tokens:.2f}, "
        f"base64={report.avg_base64_tokens:.2f}, adaptive={report.avg_adaptive_tokens:.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        decoded = decode_message(args.encoded_message)
        print(render_message_human(decoded))
        return 0

    if args.command == "tap":
        event = emit_event(
            correlation_id="tap",
            source_id="tap",
            destination_id="tap",
            instruction="HEARTBEAT",
            payload_size_bytes=0,
            total_size_bytes=0,
            latency_ms=0.0,
            status="success",
            signature_verified=False,
        )
        if args.ws:
            print(event.to_json_line())
        return 0

    if args.command == "replay":
        for line in Path(args.logfile).read_text(encoding="utf-8").splitlines():
            print(line)
        return 0

    if args.command == "token-benchmark":
        _print_token_table()
        return 0

    if args.demo:
        run_demo()
        return 0
    if args.benchmark:
        summary = benchmark_v001_vs_v002()
        tp = benchmark_encode_decode_throughput()
        eager, lazy = benchmark_decode_cpu_before_after()
        memory = benchmark_memory_allocations()
        adaptive_gain = benchmark_adaptive_repeated_exchange_percent()
        print("Benchmark JSON vs Logorrhythm base64 vs Logorrhythm binary")
        for m in summary.scenarios:
            print(
                f"{m.name}: chars json/base64 {m.json_chars}->{m.b64_chars}; "
                f"bytes json/base64/binary {m.json_bytes}->{m.b64_bytes}->{m.binary_bytes}"
            )
        print(f"total chars: {summary.total_json_chars} -> {summary.total_b64_chars} ({summary.char_reduction_percent:.2f}% reduction)")
        print(f"total bytes json->binary: {summary.total_json_bytes} -> {summary.total_binary_bytes} ({summary.byte_reduction_percent:.2f}% reduction)")
        print(f"encode throughput: {tp.encode_messages_per_sec:.0f} msg/s")
        print(f"decode throughput: {tp.decode_messages_per_sec:.0f} msg/s")
        print(f"decode CPU eager->{eager:.4f}s lazy->{lazy:.4f}s")
        print(f"memory avg bytes/message: {memory.avg_bytes_per_message:.2f}")
        print(f"memory avg allocations/message: {memory.avg_allocations_per_message:.4f}")
        print(f"adaptive repeated exchange gain: {adaptive_gain:.2f}%")
        return 0
    if args.v003_dashboard:
        print(build_v003_dashboard().to_markdown())
        return 0
    if args.sync_benchmark_table:
        print(sync_readme_benchmark_table())
        return 0
    if args.generate_graphs:
        print("\n".join(sync_graph_artifacts()))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
