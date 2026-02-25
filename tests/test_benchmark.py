import unittest

from logorrhythm.benchmark import (
    benchmark_memory_allocations,
    benchmark_tokens,
    benchmark_v001_vs_v002,
)


class BenchmarkTests(unittest.TestCase):
    def test_v002_improves_over_v001(self):
        summary = benchmark_v001_vs_v002()
        self.assertGreater(summary.total_json_chars, summary.total_b64_chars)
        self.assertGreater(summary.total_json_bytes, summary.total_binary_bytes)
        for scenario in summary.scenarios:
            self.assertGreater(scenario.json_bytes, scenario.binary_bytes, msg=f"Expected binary to reduce bytes for {scenario.name}")

    def test_token_benchmark_has_expected_scenarios(self):
        report = benchmark_tokens(runs=2)
        names = {s.name for s in report.scenarios}
        self.assertEqual(names, {"single_control", "repeated_coordination", "structured_payload", "nested_payload"})
        for scenario in report.scenarios:
            self.assertGreater(scenario.json_tokens, 0)
            self.assertGreater(scenario.base64_tokens, 0)
            self.assertGreater(scenario.adaptive_tokens, 0)

    def test_memory_microbenchmark_non_negative(self):
        metrics = benchmark_memory_allocations(iterations=200)
        self.assertGreaterEqual(metrics.avg_bytes_per_message, 0.0)
        self.assertGreaterEqual(metrics.avg_allocations_per_message, 0.0)


if __name__ == "__main__":
    unittest.main()
