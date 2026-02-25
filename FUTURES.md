# FUTURES: Beyond Message Passing

## Status note for v0.0.5 efficiency track
The following modules remain in-tree for compatibility and research, but are **experimental/future-facing** and not part of the core encoding efficiency path (`encoding.py`, `adaptive.py`, `benchmark.py`):
- `registry.py`
- `routing/`
- `plugins/`
- `topology.py`
- `cross_model.py`

## 1) Shared-state swarm fabric
Agents write/read typed state cells instead of exchanging point-to-point messages. Scheduler wakes agents by state-delta predicates.

## 2) Blackboard architecture
A global priority board stores tasks, confidence, and partial proofs. Agents pull highest-value unresolved cells; merge policy resolves conflicts deterministically.

## 3) Superposition-inspired execution
Agents keep multiple probable task states with confidence amplitudes. Observation (commit trigger) collapses to a concrete plan branch.

## 4) Why explore this
Message passing scales well for isolation, but can overpay in routing overhead at 10k+ agents. Alternate coordination models may reduce coordination bytes further.
