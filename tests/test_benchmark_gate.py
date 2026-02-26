import unittest

from logorrhythm.benchmark import break_even_count, run_adversarial_unique, run_validation_matrix


class BenchmarkGateTests(unittest.TestCase):
    def test_break_even_is_found_for_repeated_stream(self):
        messages = [{"id": 7, "cmd": "scan", "target": "x", "value": 99}]
        be = break_even_count(messages)
        self.assertIsNotNone(be)
        self.assertGreaterEqual(be, 1)

    def test_validation_matrix_shape_and_stats(self):
        matrix = run_validation_matrix(scales=(1, 10, 100), runs=2)
        self.assertEqual(matrix["runs"], 2)
        self.assertEqual(matrix["scales"], [1, 10, 100])
        self.assertEqual(len(matrix["rows"]), 9)
        for row in matrix["rows"]:
            self.assertIn("avg", row["json_bytes"])
            self.assertIn("stdev", row["cpu_us_per_message"])
            self.assertGreater(row["handshake_total"]["avg"], 0)
            self.assertIn("hello", row["handshake_breakdown"])

    def test_repeated_scenario_break_even_by_10k(self):
        matrix = run_validation_matrix(scales=(10000,), runs=2)
        repeated = next(r for r in matrix["rows"] if r["scenario_key"] == "repeated")
        self.assertIsNotNone(repeated["break_even"])

    def test_adversarial_runner_reports_rows(self):
        result = run_adversarial_unique(scales=(1000,), runs=2)
        self.assertEqual(result["scales"], [1000])
        self.assertEqual(len(result["rows"]), 1)
        self.assertIn("savings_pct", result["rows"][0])


if __name__ == "__main__":
    unittest.main()
