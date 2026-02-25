import unittest

from logorrhythm.v003 import build_v003_dashboard


class V003DashboardTests(unittest.TestCase):
    def test_dashboard_shows_improvement(self):
        dashboard = build_v003_dashboard(agent_counts=(8, 32), messages_per_agent=10, seed=1)

        self.assertEqual(len(dashboard.scale_results), 2)
        for result in dashboard.scale_results:
            self.assertGreater(result.byte_reduction_percent, 0.0)
            self.assertGreater(result.avg_latency_reduction_percent, 0.0)
            self.assertGreater(result.throughput_gain_percent, 0.0)

    def test_markdown_contains_sections(self):
        dashboard = build_v003_dashboard(agent_counts=(8,), messages_per_agent=5, seed=2)
        report = dashboard.to_markdown()

        self.assertIn("LOGORRHYTHM v0.0.3 Iteration Dashboard", report)
        self.assertIn("Hyperdrive v0.0.3 Framework", report)
        self.assertIn("Shields (security hardening status)", report)

    def test_reject_zero_messages_per_agent(self):
        with self.assertRaisesRegex(ValueError, "messages_per_agent"):
            build_v003_dashboard(agent_counts=(8,), messages_per_agent=0, seed=2)

    def test_reject_non_positive_agent_counts(self):
        with self.assertRaisesRegex(ValueError, "agent_counts"):
            build_v003_dashboard(agent_counts=(8, 0), messages_per_agent=5, seed=2)


if __name__ == "__main__":
    unittest.main()
