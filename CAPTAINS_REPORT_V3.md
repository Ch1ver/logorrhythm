# CAPTAINS_REPORT_V3

## JSON baseline description
- Baseline is `json.dumps(payload, separators=(",", ":"))` (minified, UTF-8 encoded, no pretty-printing).
- Baseline payload uses exact logical shape: `{"opcode":"TASK","fields":{...}}` with identical field names and values as session input.
- No padding/extra metadata is added to JSON baseline.
- Baseline sample bytes (decoded): `{"opcode":"TASK","fields":{"id":7,"cmd":"scan","target":"node-0","value":99}}`

## Handshake cost breakdown
- HELLO bytes: 3.00
- SCHEMA_FINGERPRINT bytes: 34.00
- SCHEMA_TRANSFER bytes: 0.00
- MODE_SWITCH bytes: 2.00
- Total handshake bytes: 41.00
- Handshake share of session total bytes (repeated scenario):
  - N=100: 2.4729%
  - N=1k: 0.2553%
  - N=10k: 0.0256%
  - N=100k: 0.0026%
- Handshake bytes are included in total wire bytes used for savings calculations.

## Structural vs adaptive savings table
| Mode | Savings % (avg) | CPU µs/msg (avg) |
|---|---:|---:|
| raw_structural | -2.60% | 13.35 |
| adaptive_enabled | 79.22% | 24.69 |
| delta_enabled | 65.19% | 28.74 |
| adaptive_plus_delta | 79.22% | 24.30 |

- Derived savings breakdown:
  - structural_only_savings_pct: -2.60%
  - additional_adaptive_savings_pct: 81.82%
  - additional_delta_savings_pct: 67.79%
  - adaptive_plus_delta_increment_pct: 0.00%

## Adversarial unique test results
- Scenario: 10 fields/message, deterministic pseudo-random 8-char values, 100% unique messages, no repetition.
- N=10000: JSON=1880000.00 bytes, Session=1240041.00 bytes, Savings=34.04%.
- N=100000: JSON=18800000.00 bytes, Session=12400041.00 bytes, Savings=34.04%.

## Nested fairness confirmation
- Logical payload equivalence confirmed: True.
- Nested dict/list values not value-table learned: True.
- Nested scenario savings avg: 34.11%.

## CPU comparison (100k)
- JSON baseline total=0.8124s, 8.12 µs/msg.
- Session RAW total=0.9579s, 9.58 µs/msg.
- Session Adaptive total=2.6196s, 26.20 µs/msg.
- RAW overhead vs JSON: 17.91%.
- Adaptive overhead vs JSON: 222.46%.

## Stability metrics (5 runs)
- Instability warning: repeated N=1 CPU variance 61.20%.
- Instability warning: mixed N=1 CPU variance 40.45%.
- Instability warning: unique N=1 CPU variance 12.00%.
- Instability warning: repeated N=10 CPU variance 13.49%.
- Instability warning: unique N=10 CPU variance 15.14%.
- Instability warning: mixed N=100 CPU variance 7.15%.
- Instability warning: unique N=100 CPU variance 6.35%.
- Instability warning: mixed N=10000 CPU variance 24.22%.
- Instability warning: unique N=10000 CPU variance 23.43%.
- Instability warning: repeated N=100000 CPU variance 9.59%.
- Instability warning: mixed N=100000 CPU variance 6.74%.
- Instability warning: unique N=100000 CPU variance 5.87%.
- Benchmark warnings:
  - warning: run-to-run CPU variance exceeded 5% in at least one scenario

Savings are scenario-dependent. Results reflect this host and workload only.
