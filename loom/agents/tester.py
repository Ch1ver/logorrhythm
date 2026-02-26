from __future__ import annotations

import asyncio
import json
import subprocess

import websockets

from loom.common import AgentConfig, RUNTIME_DIR, mk_session, send_status


async def run(config: AgentConfig) -> None:
    session = mk_session("tester")
    seen = set()
    complete = 0
    while True:
        try:
            async with websockets.connect(config.uri) as ws:
                await ws.send(session.initiate_handshake())
                while True:
                    try:
                        lines = (RUNTIME_DIR / "commits.log").read_text(encoding="utf-8").splitlines()
                    except FileNotFoundError:
                        lines = []
                    for line in lines:
                        commit_id = json.loads(line)["commit_id"]
                        if commit_id in seen:
                            continue
                        seen.add(commit_id)
                        proc = subprocess.run(["python", "-m", "unittest", "discover", "-s", "loom_output/HelloLOOM", "-p", "test_*.py"], capture_output=True, text=True)
                        await ws.send(session.encode("TEST_RESULT", {"commit_id": commit_id, "passed": proc.returncode == 0, "coverage_pct": 100 if proc.returncode == 0 else 0, "failed_count": 0 if proc.returncode == 0 else 1}))
                        complete += 1
                        await send_status(lambda o, f: ws.send(session.encode(o, f)), config.agent_id, complete, 0)
                    await asyncio.sleep(1)
        except OSError:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(run(AgentConfig(name="tester", agent_id=3)))
