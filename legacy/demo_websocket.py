"""Two-process style WebSocket transport demo."""

import asyncio

from logorrhythm.transport_ws import exchange_once


async def main() -> None:
    echoed = await exchange_once(message="agent-handoff")
    print("echoed:", echoed)


if __name__ == "__main__":
    asyncio.run(main())
