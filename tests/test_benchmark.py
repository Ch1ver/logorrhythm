import unittest

from logorrhythm.benchmark import benchmark_v001_vs_v002


class BenchmarkTests(unittest.TestCase):
    def test_v002_improves_over_v001(self):
        summary = benchmark_v001_vs_v002()
        self.assertGreater(summary.total_json_chars, summary.total_b64_chars)
        self.assertGreater(summary.total_json_bytes, summary.total_binary_bytes)
        for scenario in summary.scenarios:
            self.assertGreater(scenario.json_bytes, scenario.binary_bytes, msg=f"Expected binary to reduce bytes for {scenario.name}")


if __name__ == "__main__":
    unittest.main()
