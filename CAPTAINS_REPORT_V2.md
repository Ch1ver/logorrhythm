# CAPTAINS_REPORT_V2

## Correctness coverage summary
- Expanded deterministic unittest coverage across schema, handshake, opcode encoding, value table behavior, delta encoding, worst-case safety, determinism, and memory/state bounds.
- Added explicit tests for schema canonical bytes stability, fingerprint drift on schema change, transfer round-trip behavior, idempotent HELLO handling, strict-mode mismatch handling, and pre-handshake RAW-mode enforcement.
- Added safety checks for corrupted frames, partial frames, and malicious varints with deterministic exceptions.

## Handshake cost breakdown
- Handshake bytes are now measured separately from steady-state opcode traffic for every scenario and scale.
- Repeated @10k: handshake avg=41.00, steady-state avg=160017.00, total avg=160058.00.
- Repeated @100k: handshake avg=41.00, steady-state avg=1600017.00, total avg=1600058.00.

## Break-even curve summary
- Repeated stream break-even: 1 messages.
- Mixed stream break-even varies by run configuration and is reported per row.
- Unique stream often has no break-even within cap for larger scales.

## Savings growth curve summary
- Repeated stream savings @10k: 79.21%.
- Repeated stream savings @100k: 79.22%.
- Growth reflects handshake amortization plus table/delta reuse.

## CPU tradeoff analysis
- Repeated @10k CPU µs/msg avg=24.53, min=24.47, max=24.66, stdev=0.11.
- Repeated @100k CPU µs/msg avg=24.71, min=24.54, max=25.00, stdev=0.25.

## Worst-case regression analysis
- Unique @100k regression vs JSON: -62.74%.
- Unique-stream behavior is bounded and benchmark warnings are emitted when regression exceeds configured thresholds.

## Determinism validation
- Determinism tests validate same-input same-wire output across runs.
- Table ID assignment and canonical schema ordering are tested for stable behavior.

## Memory bound validation
- Value table cap and long-session growth bounds are validated with large deterministic loops.
- Session.reset() tests ensure learned state is cleared.

## Benchmark gate warnings
- none
