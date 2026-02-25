# Changelog

## 0.0.6

- Added binary-first transport as default for `encode_message` with explicit base64 compatibility mode.
- Compacted binary header by packing message type + flags into a control byte.
- Kept zero-copy decode path (`payload_view`) as hot-path default, with explicit bytes materialization retained.
- Expanded token benchmarking with multi-scenario reporting and average-over-runs output.
- Added adaptive repeated-exchange benchmarking and surfaced compression gains in CLI/docs.
- Promoted deterministic benchmark/graph reporting for release and CI readability.

## 0.0.5

- Added v2 envelope support, security primitives, and benchmark synchronization workflow.
