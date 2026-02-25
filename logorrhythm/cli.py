"""CLI entrypoints for LOGORRHYTHM."""

from __future__ import annotations

import argparse

from ._demo_core import run_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LOGORRHYTHM command line interface")
    parser.add_argument("--demo", action="store_true", help="Run the v0.0.1 demo")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.demo:
        run_demo()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
