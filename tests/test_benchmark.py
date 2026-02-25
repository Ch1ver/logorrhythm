import unittest

from logorrhythm.benchmark import benchmark_v001_vs_v002


class BenchmarkTests(unittest.TestCase):
    def test_v002_improves_over_v001(self):
        summary = benchmark_v001_vs_v002()
        self.assertGreater(summary.total_v001_chars, summary.total_v002_chars)
        self.assertGreater(summary.total_v001_bytes, summary.total_v002_bytes)
        for scenario in summary.scenarios:
            self.assertGreater(
                scenario.v001_bytes,
                scenario.v002_bytes,
                msg=f"Expected v0.0.2 to reduce bytes for {scenario.name}",
            )


if __name__ == "__main__":
    unittest.main()
