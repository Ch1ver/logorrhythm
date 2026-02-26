from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from logorrhythm import Session, load_schema

SCHEMA_PATH = Path("schemas/loom_schema.json")
RUNTIME_DIR = Path("loom/runtime")
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AgentConfig:
    name: str
    agent_id: int
    uri: str = "ws://127.0.0.1:8765"


def mk_session(role: str) -> Session:
    s = Session(schema=load_schema(SCHEMA_PATH), role=role)
    s.mode = "OPCODE_MODE"
    s.handshake_complete = True
    return s


def now_ts() -> float:
    return time.time()


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")


async def send_status(send, agent_id: int, complete: int, pending: int, health: int = 0) -> None:
    await send(
        "STATUS_PULSE",
        {
            "agent_id": agent_id,
            "tasks_complete": complete,
            "tasks_pending": pending,
            "health": health,
        },
    )


def estimate_tokens_from_json(json_text: str) -> int:
    return max(1, len(json_text) // 4)
