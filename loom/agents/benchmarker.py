from __future__ import annotations

import asyncio
import subprocess

import websockets

from loom.common import AgentConfig, RUNTIME_DIR, mk_session, send_status


async def run(config: AgentConfig) -> None:
    session = mk_session("bench")
    seen = set()
    complete = 0
    baseline = None
    while True:
        try:
            async with websockets.connect(config.uri) as ws:
                await ws.send(session.initiate_handshake())
                while True:
                    try:
                        commits = (RUNTIME_DIR / "test_pass.log").read_text(encoding="utf-8").splitlines()
                    except FileNotFoundError:
                        commits = []
                    for c in commits:
                        commit_id = int(c)
                        if commit_id in seen:
                            continue
                        seen.add(commit_id)
                        out = subprocess.run(["python", "loom_output/HelloLOOM/benchmark.py"], capture_output=True, text=True)
                        value = int(float((out.stdout or "0").strip() or "0"))
                        if baseline is None:
                            baseline = value
                        delta = int(((value - baseline) / max(baseline, 1)) * 100)
                        await ws.send(session.encode("BENCH_RESULT", {"version": commit_id, "metric_id": 1, "value": value, "delta_pct": delta}))
                        (RUNTIME_DIR / "bench_done.log").write_text(f"{commit_id}\n", encoding="utf-8")
                        complete += 1
                        await send_status(lambda o, f: ws.send(session.encode(o, f)), config.agent_id, complete, 0)
                    await asyncio.sleep(1)
        except OSError:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(run(AgentConfig(name="bench", agent_id=4)))
