from __future__ import annotations

import asyncio
from pathlib import Path

import websockets

from loom.common import AgentConfig, mk_session


async def run(config: AgentConfig) -> None:
    session = mk_session("reporter")
    while True:
        try:
            async with websockets.connect(config.uri) as ws:
                while True:
                    msg = await ws.recv()
                    if not msg or msg[0] != 16:
                        continue
                    decoded = session.decode(msg)
                    if decoded["opcode"] == "REPORT_REQUEST":
                        summary = Path("loom/runtime/progress.jsonl").read_text(encoding="utf-8") if Path("loom/runtime/progress.jsonl").exists() else ""
                        Path("loom_report.md").write_text("# LOOM Report\n\n" + summary, encoding="utf-8")
                        await ws.send(session.encode("REPORT_RESULT", {"status": 0, "message": "report_ready"}))
        except OSError:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(run(AgentConfig(name="reporter", agent_id=6)))
