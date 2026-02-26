# LOOM

LOOM (Logorrhythm Orchestrated Operations Manager) is a 6-agent autonomous development orchestrator built on Logorrhythm opcode sessions. ARCHITECT reads `brief.md`, creates/resumes `task_graph.json`, and coordinates BUILDER, TESTER, BENCHMARKER, CRITIC, and REPORTER using binary opcodes only.

Launch with:

`python -m loom.start --brief brief.md`

Each cycle assigns a task, builds code, runs tests, benchmarks throughput, applies critic verdicts, logs progress, and emits a final report. Startup also writes `loom_efficiency.log` comparing Logorrhythm byte cost against JSON-style natural language payloads for a full orchestration cycle.

Artifacts from the proof run are written to `loom_output/HelloLOOM` and `loom/runtime/`.
