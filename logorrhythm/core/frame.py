"""Binary framing and integer codec helpers."""

from __future__ import annotations

from .errors import DecodingError


def encode_uvarint(value: int) -> bytes:
    if value < 0:
        raise ValueError("uvarint cannot encode negatives")
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode_uvarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    value = 0
    shift = 0
    i = offset
    while i < len(data):
        b = data[i]
        value |= (b & 0x7F) << shift
        i += 1
        if not (b & 0x80):
            return value, i
        shift += 7
        if shift > 63:
            raise DecodingError("uvarint too large")
    raise DecodingError("truncated uvarint")


def zigzag_encode(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def zigzag_decode(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def encode_svarint(value: int) -> bytes:
    return encode_uvarint(zigzag_encode(value))


def decode_svarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    v, pos = decode_uvarint(data, offset)
    return zigzag_decode(v), pos


def encode_bytes(value: bytes) -> bytes:
    return encode_uvarint(len(value)) + value


def decode_bytes(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    ln, pos = decode_uvarint(data, offset)
    end = pos + ln
    if end > len(data):
        raise DecodingError("truncated bytes")
    return data[pos:end], end


def encode_str(value: str) -> bytes:
    return encode_bytes(value.encode("utf-8"))


def decode_str(data: bytes, offset: int = 0) -> tuple[str, int]:
    b, pos = decode_bytes(data, offset)
    return b.decode("utf-8"), pos


def make_frame(frame_type: int, payload: bytes) -> bytes:
    return bytes((frame_type,)) + encode_uvarint(len(payload)) + payload


def parse_frame(data: bytes) -> tuple[int, bytes]:
    if not data:
        raise DecodingError("empty frame")
    frame_type = data[0]
    ln, pos = decode_uvarint(data, 1)
    end = pos + ln
    if end != len(data):
        raise DecodingError("frame length mismatch")
    return frame_type, data[pos:end]
