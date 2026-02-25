# Captain's Report — LOGORRHYTHM v0.0.6 Hardening Audit

_Date:_ 2026-02-25

## Executive summary

- Performance claims in README/graph sync were overly static and partially misleading for runtime reality.
- Core runtime path remains lightweight (`logorrhythm` import ~60–70 ms cold-process median on this host).
- Adaptive compression is strong for repeated exchanges, but regresses on unique streams (negative savings).
- Token savings are not consistent across prompt-safe binary representations; some scenarios increase tokens.

## 1) Benchmark validation

### Matrix covered

- Small control message
- Medium payload (5–10 fields)
- Nested payload
- Repeated exchanges at 100 / 1k / 10k cycles

### Results (this host)

#### Byte size (JSON vs Logorrhythm)

| Scenario | JSON bytes | Logorrhythm binary bytes | Logorrhythm base64 bytes |
|---|---:|---:|---:|
| Small control | 24 | 34 | 47 |
| Medium payload | 129 | 139 | 187 |
| Nested payload | 151 | 161 | 216 |

Observation: for raw JSON blobs embedded as payload, envelope overhead can make Logorrhythm larger. Prior fixed-size claims were workload-specific and should not be generalized.

#### Token count (tiktoken `cl100k_base` on this host)

| Scenario | JSON tokens | Base64 tokens | Binary-as-hex tokens |
|---|---:|---:|---:|
| Small control | 6 | 12 | 17 |
| Medium payload | 33 | 47 | 70 |
| Nested payload | 38 | 54 | 81 |

Observation: token reduction does **not** hold consistently for prompt-safe transport forms in these realistic scenarios.

#### Throughput over 7 runs (50,000 iterations/run)

- Encode msg/s: avg **644,399**, stdev **82,241**, worst **453,865**
- Decode msg/s: avg **99,185**, stdev **4,266**, worst **93,051**

#### Adaptive repeated exchange compression

- 100 exchanges: **82.24%** improvement (deterministic in current implementation)
- 1,000 exchanges: **83.824%** improvement
- 10,000 exchanges: **83.9824%** improvement
- Worst-case unique-stream scenario (1,000 unique messages): **-25.71%** (regression)

## 2) Runtime weight audit

### Cold import time (7 process runs)

- `import logorrhythm`: median ~**0.062 s**
- `import logorrhythm.encoding`: median ~**0.062 s**
- `import logorrhythm.api`: median ~**0.061 s**

### Runtime dependency path (core encoding)

Core imports are stdlib-only plus internal modules:
- stdlib: `base64`, `binascii`, `hashlib`, `hmac`, `json`, `re`, `struct`, `uuid`, `dataclasses`
- internal: `logorrhythm.spec`, `logorrhythm.exceptions`

Confirmed:
- `matplotlib` not imported in runtime core path
- token libraries not imported in runtime core path (`tiktoken` only lazy-imported in benchmark helper)
- CLI modules not imported by `logorrhythm.encoding`

### Dependency footprint correction

`matplotlib` removed from package runtime dependencies in `pyproject.toml` to avoid unnecessary install/runtime weight.

## 3) Performance risk review

- No blocking I/O in encode/decode hot path.
- `struct.Struct` objects compiled once at import (`_HEADER_STRUCT`, `_NONCE_STRUCT`, etc.).
- `DecodedMessage.payload_view` provides zero-copy default access.
- `DecodedMessage.payload` still allocates bytes copy by design (non-default path).
- Average decode allocation (payload_view path):
  - ~**0.0328 bytes/message**
  - ~**0.00025 allocations/message**

## 4) Token economics validation

Across realistic coordination payloads used in this audit:
- JSON baseline consistently used fewer tokens than base64 or binary-hex prompt-safe forms.
- Adaptive aliasing can reduce repeated control stream tokens materially, but only after warmup and only for repeated messages.

Conclusion: a blanket “30%+ token reduction” is not valid across mixed realistic patterns.

## 5) Tech debt cleanup executed

- Removed hard-coded benchmark claims from README and sync table; replaced with scenario/host-dependent framing.
- Replaced deterministic benchmark constants in `v004` metrics shim with explicit placeholder compatibility values.
- Updated tests to validate stable schema/keys rather than inflated numeric guarantees.
- Removed unnecessary `matplotlib` runtime dependency.

## 6) Adoption simulation (10,000 coordination messages)

This host, Python process benchmark:
- JSON encode+decode total: **0.123 s**
- Logorrhythm compact encode+decode total: **0.164 s**

Interpretation:
- Runtime overhead is measurable and can exceed JSON in pure local CPU loop, depending on payload shape.
- Benefits are most compelling when wire compactness and repeated adaptive streams dominate over local encode/decode CPU cost.

GitHub/pip installation penalty:
- No runtime penalty once installed beyond dependency footprint and import cost.
- Reducing unnecessary dependencies (e.g., `matplotlib`) lowers install and cold-start burden.

## 7) Recommendation

**Iterate further before publicizing broad performance claims.**

- Keep v0.0.6 core functionality.
- Roll back universal performance/token claims.
- Publish benchmark results with explicit scenario matrix, run count, variance, and worst-case counterexamples.
