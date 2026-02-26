from __future__ import annotations

import asyncio
from pathlib import Path

import websockets

from loom.common import AgentConfig, RUNTIME_DIR, mk_session, send_status


async def run(config: AgentConfig) -> None:
    session = mk_session("critic")
    seen = set()
    complete = 0
    while True:
        try:
            async with websockets.connect(config.uri) as ws:
                await ws.send(session.initiate_handshake())
                while True:
                    try:
                        commits = (RUNTIME_DIR / "bench_done.log").read_text(encoding="utf-8").splitlines()
                    except FileNotFoundError:
                        commits = []
                    for c in commits:
                        commit_id = int(c)
                        if commit_id in seen:
                            continue
                        seen.add(commit_id)
                        ok = Path("loom_output/HelloLOOM/README.md").exists()
                        await ws.send(session.encode("CRITIC_VERDICT", {"commit_id": commit_id, "verdict": 0 if ok else 1, "reason_code": 0 if ok else 3}))
                        complete += 1
                        await send_status(lambda o, f: ws.send(session.encode(o, f)), config.agent_id, complete, 0 if ok else 1)
                    await asyncio.sleep(1)
        except OSError:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(run(AgentConfig(name="critic", agent_id=5)))
