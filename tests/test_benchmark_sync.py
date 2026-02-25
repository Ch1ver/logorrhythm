import tempfile
import unittest
from pathlib import Path

from logorrhythm.benchmark_sync import (
    BENCHMARK_TABLE_END,
    BENCHMARK_TABLE_START,
    sync_graph_artifacts,
    sync_readme_benchmark_table,
)


class BenchmarkSyncTests(unittest.TestCase):
    def test_sync_uses_markers_and_is_idempotent(self):
        seed = (
            "# demo\n"
            f"{BENCHMARK_TABLE_START}\n"
            "old-table\n"
            f"{BENCHMARK_TABLE_END}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text(seed, encoding="utf-8")

            first_table = sync_readme_benchmark_table(str(readme))
            first_text = readme.read_text(encoding="utf-8")
            second_table = sync_readme_benchmark_table(str(readme))
            second_text = readme.read_text(encoding="utf-8")

        self.assertEqual(first_table, second_table)
        self.assertEqual(first_text, second_text)
        self.assertIn(BENCHMARK_TABLE_START, first_text)
        self.assertIn(BENCHMARK_TABLE_END, first_text)

    def test_sync_rejects_invalid_marker_layout(self):
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text("no markers here", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "start/end marker pair"):
                sync_readme_benchmark_table(str(readme))

    def test_graph_generation_writes_svg_text_files(self):
        with tempfile.TemporaryDirectory() as td:
            generated = sync_graph_artifacts(td)
            self.assertEqual(len(generated), 3)
            for path in generated:
                self.assertTrue(path.endswith(".svg"))
                text = Path(path).read_text(encoding="utf-8")
                self.assertIn("<svg", text)


if __name__ == "__main__":
    unittest.main()
