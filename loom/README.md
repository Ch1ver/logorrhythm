# LOOM

LOOM (Logorrhythm Orchestrated Operations Manager) is a lightweight autonomous orchestrator that runs a fixed multi-agent software loop over Logorrhythm opcode sessions. You provide a `brief.md`; LOOM spins an architect loop, coordinates agents, and writes outputs to `loom_output/` plus runtime logs/report files.

## 6-agent architecture
- **Architect (`loom/start.py`)**: reads the brief, creates/resumes `task_graph.json`, assigns tasks, tracks progress, and requests final reporting.
- **Builder**: materializes project artifacts for assigned tasks (current default flow writes the HelloLOOM implementation bundle).
- **Tester**: runs unit tests and sends pass/fail + coverage signals.
- **Benchmarker**: runs throughput benchmark scripts and reports value + delta.
- **Critic**: applies a basic verdict gate over produced artifacts.
- **Reporter**: compiles progress events into `loom_report.md`.

## Writing `brief.md`
Use simple `Key: Value` lines. Minimum useful fields:

```md
Project: HelloLOOM
Vision: Build a Python CLI that returns whether a number is prime.
Success criteria: Tests pass; benchmark > 10000 checks/sec; README exists.
Constraints: Pure Python, no external dependencies.
```

## Launch
```bash
python -m loom.start --brief brief.md
```

Optional token budget guardrail:

```bash
python -m loom.start --brief brief.md --token-budget 5000
```

## Expected outputs
On completion, expect:
- `loom_output/HelloLOOM/` (code, tests, benchmark, README)
- `loom/runtime/progress.jsonl` and runtime logs
- `task_graph.json` with status updates
- `loom_report.md` final summary stub
