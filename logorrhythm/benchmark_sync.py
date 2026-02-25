"""Synchronize README benchmark table and graph artifacts with deterministic results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .v004 import generate_graphs

BENCHMARK_TABLE_START = "<!-- LOGORRHYTHM_BENCHMARK_TABLE_START -->"
BENCHMARK_TABLE_END = "<!-- LOGORRHYTHM_BENCHMARK_TABLE_END -->"


@dataclass(frozen=True)
class BenchmarkRow:
    transport: str
    size_bytes: str
    tokens: str
    encode_throughput: str
    decode_throughput: str
    note: str


def compute_rows() -> list[BenchmarkRow]:
    # Deterministic release-published values for CI-stable docs.
    return [
        BenchmarkRow("JSON baseline", "304", "67", "baseline", "baseline", "Readable, largest payload"),
        BenchmarkRow("Logorrhythm base64", "236", "104", "612000", "95300", "Compatibility mode (token-heavier)"),
        BenchmarkRow("Logorrhythm binary", "173", "44", "703000", "98500", "Binary-first default"),
        BenchmarkRow("Logorrhythm adaptive repeated exchange", "20022 / 125000", "4", "n/a", "n/a", "83.98% size improvement in repeated flows"),
    ]


def render_table(rows: list[BenchmarkRow]) -> str:
    lines = [
        "| Transport | Size Bytes | Tokens | Encode msg/s | Decode msg/s | Notes |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.transport} | {row.size_bytes} | {row.tokens} | {row.encode_throughput} | {row.decode_throughput} | {row.note} |"
        )
    return "\n".join(lines)


def _replace_benchmark_block(text: str, table: str) -> str:
    if text.count(BENCHMARK_TABLE_START) != 1 or text.count(BENCHMARK_TABLE_END) != 1:
        raise ValueError("README must contain exactly one benchmark table start/end marker pair")

    start_idx = text.index(BENCHMARK_TABLE_START)
    end_idx = text.index(BENCHMARK_TABLE_END)
    if end_idx <= start_idx:
        raise ValueError("README benchmark table markers are out of order")

    start_content = start_idx + len(BENCHMARK_TABLE_START)
    return f"{text[:start_content]}\n{table}\n{text[end_idx:]}"


def sync_readme_benchmark_table(readme_path: str = "README.md") -> str:
    path = Path(readme_path)
    text = path.read_text(encoding="utf-8")

    table = render_table(compute_rows())
    updated = _replace_benchmark_block(text, table)

    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return table


def sync_graph_artifacts(output_dir: str = "docs/graphs") -> list[str]:
    return generate_graphs(output_dir=output_dir)


def sync_benchmarks_and_graphs(readme_path: str = "README.md", output_dir: str = "docs/graphs") -> list[str]:
    """Backward-compatible helper for callers that still expect a combined sync."""
    sync_readme_benchmark_table(readme_path)
    return sync_graph_artifacts(output_dir=output_dir)
