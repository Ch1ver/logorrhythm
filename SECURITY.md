# LOGORRHYTHM Security Notes (v0.0.3 planning)

This project currently provides protocol-level integrity controls and strict decoding checks. For production-grade multi-agent deployments, apply the following hardening layers.

## Current built-in protections

- CRC32 checksum verification for payload corruption detection.
- Exact payload-length validation against header metadata.
- Capability and flag validation with reserved-bit rejection.
- Unknown agent/instruction code rejection.
- UTF-8 decoding validation for semantic payload content.

## Repository and source-code shield recommendations

1. Enable branch protection on `main`:
   - require pull request reviews,
   - require passing tests,
   - block force pushes.
2. Enforce signed commits and verified authorship.
3. Add dependency scanning (`pip-audit`/`safety`) in CI.
4. Add secret scanning (GitHub Advanced Security or equivalent).
5. Generate SBOM artifacts and attach to releases.

## Runtime and transport shield recommendations (v0.0.3+)

1. Introduce signed transport mode using the `SIGNED` capability.
2. Add replay protection (sequence IDs + timestamp windows).
3. Add backpressure and quota controls for flood resistance.
4. Add per-agent authentication and authorization policy.
5. Add structured security telemetry (auth failures, malformed frames, replay attempts).

## Operational checklist

- [ ] CI checks are mandatory before merge.
- [ ] Release artifacts are signed.
- [ ] Secrets are never committed; rotate immediately if leaked.
- [ ] Security incident contact/triage path is documented.
