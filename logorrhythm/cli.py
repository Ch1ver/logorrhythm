from __future__ import annotations

import argparse
import json

from .benchmark import run_agent_scale_compare, run_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--compare-legacy", action="store_true")
    args = parser.parse_args()
    if args.benchmark:
        print(json.dumps(run_all(), indent=2))
    if args.compare_legacy:
        print(json.dumps(run_agent_scale_compare(), indent=2))


if __name__ == "__main__":
    main()
