# FUTURES: Beyond Message Passing

## 1) Shared-state swarm fabric
Agents write/read typed state cells instead of exchanging point-to-point messages. Scheduler wakes agents by state-delta predicates.

## 2) Blackboard architecture
A global priority board stores tasks, confidence, and partial proofs. Agents pull highest-value unresolved cells; merge policy resolves conflicts deterministically.

## 3) Superposition-inspired execution
Agents keep multiple probable task states with confidence amplitudes. Observation (commit trigger) collapses to a concrete plan branch.

## 4) Why explore this
Message passing scales well for isolation, but can overpay in routing overhead at 10k+ agents. Alternate coordination models may reduce coordination bytes further.
