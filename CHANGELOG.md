# Changelog

## 0.1.0

- **Breaking pivot** to a session-negotiated opcode protocol.
- Added new core modules:
  - `logorrhythm/core/session.py`
  - `logorrhythm/core/schema.py`
  - `logorrhythm/core/tables.py`
  - `logorrhythm/core/frame.py`
  - `logorrhythm/core/errors.py`
- Added fingerprint-based handshake with optional schema transfer and safe RAW fallback.
- Added adaptive value table learning threshold and per-field delta encoding.
- Replaced benchmark focus with session scenarios (A/B/C: repeated, mixed, unique).
- Moved older envelope/base64-era modules into `logorrhythm/legacy/`.
- Replaced previous tests with deterministic `unittest` coverage for the new protocol core.

## 0.0.6

- Legacy pre-pivot release (retained in `logorrhythm/legacy/`).
