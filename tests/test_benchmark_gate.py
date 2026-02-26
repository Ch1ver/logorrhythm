import unittest

from logorrhythm.benchmark import break_even_count, run_all


class BenchmarkGateTests(unittest.TestCase):
    def test_break_even_is_found(self):
        messages = [{"id": 7, "cmd": "scan", "target": "x", "value": 99}]
        be = break_even_count(messages)
        self.assertIsNotNone(be)
        self.assertGreaterEqual(be, 1)

    def test_savings_hold_at_10k(self):
        rows = run_all((10000,))
        by_name = {r["scenario"]: r for r in rows}
        self.assertGreater(by_name["A_repeated"]["savings_pct_vs_json"], 50.0)
        self.assertGreater(by_name["B_mixed"]["savings_pct_vs_json"], 50.0)
        self.assertGreater(by_name["C_unique"]["savings_pct_vs_json"], 40.0)
        self.assertLess(by_name["A_repeated"]["cpu_us_per_message"], 1000.0)


if __name__ == "__main__":
    unittest.main()
