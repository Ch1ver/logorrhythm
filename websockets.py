"""Minimal local fallback for websocket-like API used by LOOM tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class _State:
    name: str = "OPEN"


class _Socket:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._r = reader
        self._w = writer
        self.state = _State()

    async def send(self, data: bytes) -> None:
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._w.write(len(data).to_bytes(4, "big") + data)
        await self._w.drain()

    async def recv(self) -> bytes:
        ln = int.from_bytes(await self._r.readexactly(4), "big")
        return await self._r.readexactly(ln)

    async def close(self) -> None:
        self.state.name = "CLOSED"
        self._w.close()
        await self._w.wait_closed()


class _ServerWrap:
    def __init__(self, server: asyncio.AbstractServer):
        self._s = server

    def close(self):
        self._s.close()

    async def wait_closed(self):
        await self._s.wait_closed()


async def serve(handler, host: str, port: int):
    async def _accept(reader, writer):
        sock = _Socket(reader, writer)
        try:
            await handler(sock)
        finally:
            if sock.state.name != "CLOSED":
                await sock.close()

    s = await asyncio.start_server(_accept, host, port)
    return _ServerWrap(s)


class _ConnectCtx:
    def __init__(self, uri: str):
        self.uri = uri
        self.sock = None

    async def __aenter__(self):
        host_port = self.uri.split("//", 1)[1]
        host, port = host_port.split(":")
        r, w = await asyncio.open_connection(host, int(port))
        self.sock = _Socket(r, w)
        return self.sock

    async def __aexit__(self, exc_type, exc, tb):
        await self.sock.close()


async def _connect_raw(uri: str):
    host_port = uri.split("//", 1)[1]
    host, port = host_port.split(":")
    r, w = await asyncio.open_connection(host, int(port))
    return _Socket(r, w)


def connect(uri: str):
    return _ConnectCtx(uri)
