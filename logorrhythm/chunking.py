"""Chunked frame transport with sequence IDs for v0.0.3."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkFrame:
    transfer_id: str
    seq_id: int
    total_chunks: int
    payload: bytes


def chunk_payload(payload: bytes, *, chunk_size: int = 512) -> list[ChunkFrame]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if not payload:
        return [ChunkFrame(transfer_id="0" * 16, seq_id=0, total_chunks=1, payload=b"")]

    transfer_id = hashlib.blake2s(payload, digest_size=8).hexdigest()
    total = (len(payload) + chunk_size - 1) // chunk_size
    frames: list[ChunkFrame] = []
    for i in range(total):
        start = i * chunk_size
        end = start + chunk_size
        frames.append(ChunkFrame(transfer_id=transfer_id, seq_id=i, total_chunks=total, payload=payload[start:end]))
    return frames


def reassemble_chunks(frames: list[ChunkFrame]) -> bytes:
    if not frames:
        return b""
    transfer_ids = {f.transfer_id for f in frames}
    if len(transfer_ids) != 1:
        raise ValueError("frames contain mixed transfer_id values")

    total_chunks = frames[0].total_chunks
    if any(f.total_chunks != total_chunks for f in frames):
        raise ValueError("inconsistent total_chunks values")

    ordered: dict[int, bytes] = {}
    for frame in frames:
        if frame.seq_id in ordered:
            raise ValueError("duplicate sequence id")
        ordered[frame.seq_id] = frame.payload

    if len(ordered) != total_chunks:
        raise ValueError("missing chunk(s) for deterministic reassembly")

    return b"".join(ordered[idx] for idx in range(total_chunks))
