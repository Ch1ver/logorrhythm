from __future__ import annotations

import asyncio
from pathlib import Path

import websockets

from loom.common import AgentConfig, RUNTIME_DIR, append_jsonl, mk_session, send_status


async def _write_hello_project(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / "helloloom.py").write_text(
        "def is_prime(n: int) -> bool:\n"
        "    if n < 2:\n        return False\n"
        "    if n % 2 == 0:\n        return n == 2\n"
        "    i = 3\n"
        "    while i * i <= n:\n"
        "        if n % i == 0:\n            return False\n"
        "        i += 2\n"
        "    return True\n\n"
        "def main() -> None:\n"
        "    import sys\n"
        "    n = int(sys.argv[1])\n"
        "    print('prime' if is_prime(n) else 'not-prime')\n\n"
        "if __name__ == '__main__':\n    main()\n",
        encoding="utf-8",
    )
    (base / "test_helloloom.py").write_text(
        "import unittest\nfrom helloloom import is_prime\n\n"
        "class PrimeTests(unittest.TestCase):\n"
        "    def test_small(self):\n"
        "        self.assertTrue(is_prime(2))\n"
        "        self.assertTrue(is_prime(13))\n"
        "        self.assertFalse(is_prime(1))\n"
        "        self.assertFalse(is_prime(21))\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n",
        encoding="utf-8",
    )
    (base / "benchmark.py").write_text(
        "import time\nfrom helloloom import is_prime\n\n"
        "def run(iterations=20000):\n"
        "    start = time.perf_counter()\n"
        "    for i in range(iterations):\n        is_prime(1000003 + (i % 97))\n"
        "    return iterations / (time.perf_counter() - start)\n\n"
        "if __name__ == '__main__':\n    print(f'{run():.2f}')\n",
        encoding="utf-8",
    )
    (base / "README.md").write_text("# HelloLOOM\n\nCLI utility for prime checking.\n", encoding="utf-8")


async def run(config: AgentConfig) -> None:
    session = mk_session("builder")
    complete = 0
    while True:
        try:
            async with websockets.connect(config.uri) as ws:
                while True:
                    msg = await ws.recv()
                    if not msg or msg[0] != 16:
                        continue
                    decoded = session.decode(msg)
                    if decoded["opcode"] != "TASK_ASSIGN":
                        continue
                    task_id = int(decoded["fields"]["task_id"])
                    await _write_hello_project(Path("loom_output/HelloLOOM"))
                    complete += 1
                    commit_id = complete
                    append_jsonl(RUNTIME_DIR / "commits.log", {"commit_id": commit_id, "task_id": task_id})
                    await ws.send(session.encode("BUILD_RESULT", {"task_id": task_id, "commit_id": commit_id, "status": 0, "token_used": 120}))
                    await send_status(lambda o, f: ws.send(session.encode(o, f)), config.agent_id, complete, 0)
        except OSError:
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(run(AgentConfig(name="builder", agent_id=2)))
