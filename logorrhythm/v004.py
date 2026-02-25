"""v0.0.6 deterministic benchmark models and graph generation (CI-safe)."""

from __future__ import annotations

from pathlib import Path


def compute_v004_metrics() -> dict[str, object]:
    """Legacy compatibility shim for prior tests/docs.

    The returned values are placeholders only and are not release guarantees.
    Use benchmark helpers for measured values.
    """
    return {
        "byte_reduction": 0.0,
        "throughput_gain": 0.0,
        "latency_improvement": 0.0,
        "encode_throughput": 0.0,
        "decode_throughput": 0.0,
        "adaptive_gain": 0.0,
    }


def _svg_header(*, width: int = 720, height: int = 420, title: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <rect width="100%" height="100%" fill="white"/>\n'
        f'  <text x="24" y="34" font-size="22" font-family="Arial">{title}</text>\n'
    )


def _svg_footer() -> str:
    return "</svg>\n"


def _write_svg(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def _bar_svg(*, title: str, labels: list[str], values: list[float], unit: str, color: str = "#1f77b4", max_value: float | None = None) -> str:
    top = max_value if max_value is not None else max(values)
    lines = [_svg_header(title=title)]
    lines.append('  <line x1="80" y1="350" x2="620" y2="350" stroke="#666"/>\n')
    lines.append('  <line x1="80" y1="80" x2="80" y2="350" stroke="#666"/>\n')
    step = 540 // len(values)
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = 120 + idx * step
        height = int((value / top) * 240) if top else 0
        y = 350 - height
        lines.append(f'  <rect x="{x-40}" y="{y}" width="80" height="{height}" fill="{color}"/>\n')
        lines.append(f'  <text x="{x-36}" y="372" font-size="12" font-family="Arial">{label}</text>\n')
        lines.append(f'  <text x="{x-36}" y="{y-8}" font-size="12" font-family="Arial">{value:.2f}{unit}</text>\n')
    lines.append(_svg_footer())
    return "".join(lines)


def _build_size_comparison_svg() -> str:
    return _bar_svg(
        title="Size Comparison: JSON vs Binary",
        labels=["JSON", "Binary"],
        values=[304.0, 173.0],
        unit="B",
        color="#1f77b4",
        max_value=320.0,
    )


def _build_token_comparison_svg() -> str:
    return _bar_svg(
        title="Token Comparison",
        labels=["JSON", "Base64", "Adaptive"],
        values=[67.0, 104.0, 4.0],
        unit="",
        color="#9467bd",
        max_value=110.0,
    )


def _build_throughput_svg() -> str:
    return _bar_svg(
        title="Encode/Decode Throughput (relative placeholder)",
        labels=["Encode", "Decode"],
        values=[1.0, 1.0],
        unit="",
        color="#2ca02c",
        max_value=750000.0,
    )


def _build_adaptive_svg() -> str:
    return _bar_svg(
        title="Adaptive Repeated Exchange Compression (placeholder)",
        labels=["Improvement"],
        values=[1.0],
        unit="%",
        color="#d62728",
        max_value=100.0,
    )


def generate_graphs(output_dir: str = "docs/graphs") -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = [
        out / "size_comparison_json_binary.svg",
        out / "token_comparison.svg",
        out / "throughput_encode_decode.svg",
        out / "adaptive_repeated_exchange.svg",
    ]
    builders = [
        _build_size_comparison_svg,
        _build_token_comparison_svg,
        _build_throughput_svg,
        _build_adaptive_svg,
    ]
    for path, builder in zip(paths, builders):
        _write_svg(path, builder())
    return [str(p) for p in paths]
