"""CLI entrypoints for LOGORRHYTHM."""

from __future__ import annotations

import argparse
from pathlib import Path

from ._demo_core import run_demo
from .benchmark import benchmark_v001_vs_v002
from .benchmark_sync import sync_graph_artifacts, sync_readme_benchmark_table
from .encoding import decode_message, render_message_human
from .observer import emit_event
from .v003 import build_v003_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOGORRHYTHM command line interface")
    parser.add_argument("--demo", action="store_true", help="Run the v0.0.2 demo")
    parser.add_argument("--benchmark", action="store_true", help="Compare v0.0.1 baseline against v0.0.2 transport")
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
    return parser


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

    if args.demo:
        run_demo()
        return 0
    if args.benchmark:
        summary = benchmark_v001_vs_v002()
        print("Benchmark v0.0.1 -> v0.0.2")
        for m in summary.scenarios:
            print(f"{m.name}: chars {m.v001_chars} -> {m.v002_chars}, bytes {m.v001_bytes} -> {m.v002_bytes}")
        print(f"total chars: {summary.total_v001_chars} -> {summary.total_v002_chars} ({summary.char_reduction_percent:.2f}% reduction)")
        print(f"total bytes: {summary.total_v001_bytes} -> {summary.total_v002_bytes} ({summary.byte_reduction_percent:.2f}% reduction)")
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
