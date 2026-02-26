from __future__ import annotations

import argparse
import json

from .benchmark import (
    SCALES_DEFAULT,
    run_adversarial_unique,
    run_agent_scale_compare,
    run_all,
    run_cpu_comparison,
    run_nested_fairness,
    run_structural_adaptive_breakdown,
    run_validation_matrix,
)
from .legacy.benchmark_sync import sync_graph_artifacts, sync_readme_benchmark_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--benchmark-extended", action="store_true")
    parser.add_argument("--compare-legacy", action="store_true")
    parser.add_argument("--sync-benchmark-table", action="store_true")
    parser.add_argument("--generate-graphs", action="store_true")
    args = parser.parse_args()

    if args.benchmark:
        print(json.dumps(run_all((1000, 10000)), indent=2))
    if args.benchmark_extended:
        print(
            json.dumps(
                {
                    "validation_matrix": run_validation_matrix(scales=SCALES_DEFAULT, runs=5),
                    "structural_adaptive_breakdown": run_structural_adaptive_breakdown(n=100000, runs=5),
                    "adversarial_unique": run_adversarial_unique(scales=(10000, 100000), runs=5),
                    "nested_fairness": run_nested_fairness(n=10000, runs=5),
                    "cpu_comparison": run_cpu_comparison(n=100000, runs=5),
                },
                indent=2,
            )
        )
    if args.compare_legacy:
        print(json.dumps(run_agent_scale_compare(), indent=2))
    if args.sync_benchmark_table:
        table = sync_readme_benchmark_table()
        print(table)
    if args.generate_graphs:
        paths = sync_graph_artifacts()
        print(json.dumps(paths, indent=2))


if __name__ == "__main__":
    main()
