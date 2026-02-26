import unittest

from logorrhythm.benchmark import run_agent_scale_compare


class BenchmarkCompareTests(unittest.TestCase):
    def test_agent_scale_compare_shape(self):
        rows = run_agent_scale_compare((1, 10, 100), rounds_per_agent=2)
        self.assertEqual([r["agents"] for r in rows], [1, 10, 100])
        self.assertEqual([r["messages"] for r in rows], [2, 20, 200])
        for row in rows:
            self.assertGreater(row["new_wire_bytes"], 0)
            self.assertGreater(row["legacy_wire_bytes"], 0)
            self.assertIsNotNone(row["new_vs_legacy_ratio"])


if __name__ == "__main__":
    unittest.main()
