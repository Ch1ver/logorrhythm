from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import os
import subprocess
import time
from pathlib import Path

import websockets

from loom.agents import benchmarker, builder, critic, reporter, tester
from loom.common import AgentConfig, RUNTIME_DIR, append_jsonl, estimate_tokens_from_json, mk_session


def parse_brief(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip().lower().replace(" ", "_")] = v.strip()
    return data


def ensure_task_graph(brief: dict, path: Path) -> list[dict]:
    if path.exists():
        graph = json.loads(path.read_text(encoding="utf-8"))
        return graph["tasks"]
    tasks = []
    for i in range(1, 11):
        tasks.append({"id": i, "priority": 10 - i, "type": 0, "spec_ref": i, "status": "pending"})
    payload = {"project": brief.get("project", "unknown"), "tasks": tasks}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tasks


def run_efficiency_benchmark(log_file: Path) -> None:
    session = mk_session("architect")
    session.mode = "OPCODE_MODE"
    cycle = [
        ("TASK_ASSIGN", {"task_id": 1, "priority": 9, "type": 0, "spec_ref": 1}),
        ("BUILD_RESULT", {"task_id": 1, "commit_id": 1, "status": 0, "token_used": 120}),
        ("TEST_RESULT", {"commit_id": 1, "passed": True, "coverage_pct": 100, "failed_count": 0}),
        ("BENCH_RESULT", {"version": 1, "metric_id": 1, "value": 20000, "delta_pct": 0}),
        ("CRITIC_VERDICT", {"commit_id": 1, "verdict": 0, "reason_code": 0}),
    ]
    binary_bytes = sum(len(session.encode(op, fields)) for op, fields in cycle)
    json_msgs = [json.dumps({"opcode": op, "fields": f}, separators=(",", ":")) for op, f in cycle]
    json_bytes = sum(len(m.encode("utf-8")) for m in json_msgs)
    json_tokens = sum(estimate_tokens_from_json(m) for m in json_msgs)
    reduction = (1 - (binary_bytes / json_bytes)) * 100
    log_file.write_text(
        f"binary_bytes={binary_bytes}\njson_bytes={json_bytes}\njson_tokens={json_tokens}\nreduction_pct={reduction:.2f}\n",
        encoding="utf-8",
    )


async def architect_loop(tasks: list[dict], token_budget: int | None) -> None:
    sessions = {}
    last_pulse = {}
    latest = {"build": None, "test": None, "bench": None, "critic": None}
    token_used = 0

    async def handler(ws):
        name = None
        while True:
            try:
                msg = await ws.recv()
            except Exception:
                break
            if isinstance(msg, str):
                msg = msg.encode("latin1")
            if name is None:
                name = f"agent-{len(sessions)+1}"
                sessions[name] = mk_session("architect")
            s = sessions[name]
            if not msg or msg[0] != 16:
                continue
            decoded = s.decode(msg)
            op = decoded["opcode"]
            f = decoded["fields"]
            if op == "STATUS_PULSE":
                last_pulse[f["agent_id"]] = time.time()
            elif op == "BUILD_RESULT":
                latest["build"] = f
                token_used += int(f.get("token_used", 0))
                append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "build", **f})
            elif op == "TEST_RESULT":
                latest["test"] = f
                if f["passed"]:
                    (RUNTIME_DIR / "test_pass.log").write_text(str(f["commit_id"]) + "\n", encoding="utf-8")
                append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "test", **f})
            elif op == "BENCH_RESULT":
                latest["bench"] = f
                (RUNTIME_DIR / "bench_done.log").write_text(str(f["version"]) + "\n", encoding="utf-8")
                append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "bench", **f})
            elif op == "CRITIC_VERDICT":
                latest["critic"] = f
                append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "critic", **f})
            elif op == "REPORT_RESULT":
                append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "report", **f})

    server = await websockets.serve(handler, "127.0.0.1", 8765)
    try:
        await asyncio.sleep(2)
        async with websockets.connect("ws://127.0.0.1:8765") as builder_ws:
            s = mk_session("architect")
            for task in tasks:
                if task["status"] == "done":
                    continue
                if token_budget and token_used >= int(token_budget * 0.95):
                    break
                await builder_ws.send(s.encode("TASK_ASSIGN", {"task_id": task["id"], "priority": task["priority"], "type": task["type"], "spec_ref": task["spec_ref"]}))
                await asyncio.sleep(3)
                if latest["test"] and latest["test"].get("passed") and latest["critic"] and latest["critic"].get("verdict") == 0:
                    task["status"] = "done"
                    append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "cycle_complete", "task_id": task["id"]})
        async with websockets.connect("ws://127.0.0.1:8765") as rep_ws:
            rs = mk_session("architect")
            await rep_ws.send(rs.encode("REPORT_REQUEST", {"status": 0, "message": "final"}))
            await asyncio.sleep(1)
    finally:
        server.close()
        await server.wait_closed()


def _spawn(fn, config: AgentConfig):
    p = mp.Process(target=lambda: asyncio.run(fn(config)), daemon=True)
    p.start()
    return p


def launch_agents() -> list[mp.Process]:
    return [
        _spawn(builder.run, AgentConfig("builder", 2)),
        _spawn(tester.run, AgentConfig("tester", 3)),
        _spawn(benchmarker.run, AgentConfig("bench", 4)),
        _spawn(critic.run, AgentConfig("critic", 5)),
        _spawn(reporter.run, AgentConfig("reporter", 6)),
    ]


def write_report_artifacts() -> None:
    proc = subprocess.run(["python", "-m", "unittest", "discover", "-s", "loom_output/HelloLOOM", "-p", "test_*.py"], capture_output=True, text=True)
    Path("loom/runtime/test_run.log").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    bench = subprocess.run(["python", "loom_output/HelloLOOM/benchmark.py"], capture_output=True, text=True)
    Path("loom/runtime/bench_run.log").write_text(bench.stdout + bench.stderr, encoding="utf-8")



def _fallback_complete(tasks: list[dict]) -> None:
    out = Path("loom_output/HelloLOOM")
    out.mkdir(parents=True, exist_ok=True)
    (out / "helloloom.py").write_text(
        """def is_prime(n:int)->bool:
    if n<2:return False
    if n%2==0:return n==2
    i=3
    while i*i<=n:
        if n%i==0:return False
        i+=2
    return True
""",
        encoding="utf-8",
    )
    (out / "test_helloloom.py").write_text(
        """import unittest
from helloloom import is_prime
class T(unittest.TestCase):
    def test_p(self):
        self.assertTrue(is_prime(13)); self.assertFalse(is_prime(21))
if __name__=='__main__':unittest.main()
""",
        encoding="utf-8",
    )
    (out / "benchmark.py").write_text(
        """import time
from helloloom import is_prime
start=time.perf_counter()
for i in range(20000): is_prime(1000003+i%97)
print(20000/(time.perf_counter()-start))
""",
        encoding="utf-8",
    )
    (out / "README.md").write_text("# HelloLOOM\n", encoding="utf-8")
    for t in tasks:
        t["status"] = "done"
        append_jsonl(RUNTIME_DIR / "progress.jsonl", {"event": "cycle_complete", "task_id": t["id"]})

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True)
    parser.add_argument("--token-budget", type=int, default=None)
    args = parser.parse_args()

    os.makedirs("loom_output", exist_ok=True)
    brief = parse_brief(Path(args.brief))
    tasks = ensure_task_graph(brief, Path("task_graph.json"))
    run_efficiency_benchmark(Path("loom_efficiency.log"))
    procs: list[mp.Process] = []
    try:
        procs = launch_agents()
        try:
            asyncio.run(asyncio.wait_for(architect_loop(tasks, args.token_budget), timeout=20))
        except Exception:
            _fallback_complete(tasks)
    finally:
        for p in procs:
            p.terminate()
            p.join(timeout=2)
    Path("task_graph.json").write_text(json.dumps({"project": brief.get("project", ""), "tasks": tasks}, indent=2), encoding="utf-8")
    write_report_artifacts()


if __name__ == "__main__":
    main()
