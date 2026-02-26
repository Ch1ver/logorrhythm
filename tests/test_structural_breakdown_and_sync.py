import tempfile
import unittest
from pathlib import Path

from logorrhythm.benchmark import run_structural_adaptive_breakdown
from logorrhythm.legacy.benchmark_sync import (
    BENCHMARK_TABLE_END,
    BENCHMARK_TABLE_START,
    sync_readme_benchmark_table,
)


class StructuralBreakdownAndSyncTests(unittest.TestCase):
    def test_structural_breakdown_uses_distinct_streams(self):
        result = run_structural_adaptive_breakdown(n=2000, runs=1)
        modes = result["modes"]
        breakdown = result["savings_breakdown"]

        self.assertIn("raw_structural_delta_baseline", modes)
        self.assertNotEqual(
            modes["adaptive_plus_delta"]["savings_pct"]["avg"],
            modes["adaptive_enabled"]["savings_pct"]["avg"],
        )

        expected_delta = (
            modes["delta_enabled"]["savings_pct"]["avg"]
            - modes["raw_structural_delta_baseline"]["savings_pct"]["avg"]
        )
        self.assertAlmostEqual(breakdown["additional_delta_savings_pct"], expected_delta)

    def test_sync_readme_benchmark_table_requires_single_marker_pair(self):
        content = "# README\n" + BENCHMARK_TABLE_START + "\nold\n" + BENCHMARK_TABLE_END + "\n"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "README.md"
            p.write_text(content, encoding="utf-8")
            sync_readme_benchmark_table(str(p))
            out = p.read_text(encoding="utf-8")
            self.assertEqual(out.count(BENCHMARK_TABLE_START), 1)
            self.assertEqual(out.count(BENCHMARK_TABLE_END), 1)


if __name__ == "__main__":
    unittest.main()
