"""Streaming protocol primitives for chunk-first cognition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


OP_STREAM_START = 0x70
OP_STREAM_CHUNK = 0x71
OP_STREAM_END = 0x72


@dataclass(frozen=True)
class StreamFrame:
    opcode: int
    stream_id: int
    chunk_index: int
    data: bytes


def encode_stream(message: str, *, stream_id: int = 1, chunk_size: int = 128) -> list[StreamFrame]:
    payload = message.encode("utf-8")
    frames = [StreamFrame(opcode=OP_STREAM_START, stream_id=stream_id, chunk_index=0, data=b"")]
    for index in range(0, len(payload), chunk_size):
        frames.append(
            StreamFrame(
                opcode=OP_STREAM_CHUNK,
                stream_id=stream_id,
                chunk_index=(index // chunk_size) + 1,
                data=payload[index : index + chunk_size],
            )
        )
    frames.append(StreamFrame(opcode=OP_STREAM_END, stream_id=stream_id, chunk_index=len(frames), data=b""))
    return frames


def iter_stream_text(frames: Iterable[StreamFrame]) -> Iterable[str]:
    for frame in frames:
        if frame.opcode == OP_STREAM_CHUNK:
            yield frame.data.decode("utf-8")
