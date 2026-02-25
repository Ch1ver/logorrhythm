import base64
import struct
import unittest

from logorrhythm.api import decode as api_decode
from logorrhythm.api import encode as api_encode
from logorrhythm.adaptive import AdaptiveCodec
from logorrhythm.encoding import decode_compact_payload, decode_message, encode_compact_payload, encode_message
from logorrhythm.exceptions import DecodingError
from logorrhythm.spec import HEADER_SIZE, AgentCode, InstructionCode, MessageType
from logorrhythm.streaming import encode_stream, iter_stream_text


class ApiAndEncodingRoundTripTests(unittest.TestCase):
    def test_api_round_trip(self):
        encoded = api_encode(task="handoff")
        self.assertEqual(api_decode(encoded), "handoff")

    def test_encoding_round_trip(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="status",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload)
        decoded = decode_message(encoded)
        compact = decode_compact_payload(decoded.payload)
        self.assertEqual(compact.task, "status")
        self.assertEqual(compact.src, AgentCode.A1)
        self.assertEqual(compact.dst, AgentCode.A2)


class DecodeFailureTests(unittest.TestCase):
    def _decode_raw(self, encoded: str) -> bytes:
        pad = "=" * ((4 - len(encoded) % 4) % 4)
        return base64.urlsafe_b64decode((encoded + pad).encode("ascii"))

    def _encode_raw(self, blob: bytes) -> str:
        return base64.urlsafe_b64encode(blob).rstrip(b"=").decode("ascii")

    def _sample_encoded(self) -> str:
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        return encode_message(message_type=MessageType.AGENT, payload=payload)

    def test_bad_base64(self):
        with self.assertRaisesRegex(DecodingError, "Invalid base64url transport"):
            decode_message("@@@")

    def test_too_short(self):
        with self.assertRaisesRegex(DecodingError, "Message too short for header"):
            decode_message("AQ")

    def test_bad_crc32(self):
        raw = bytearray(self._decode_raw(self._sample_encoded()))
        raw[HEADER_SIZE] ^= 0x01
        with self.assertRaisesRegex(DecodingError, "CRC32 checksum mismatch"):
            decode_message(self._encode_raw(bytes(raw)))

    def test_payload_length_mismatch(self):
        raw = self._decode_raw(self._sample_encoded())
        version, mt, flags, caps, payload_len, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags, caps, payload_len + 1, crc)
        with self.assertRaisesRegex(DecodingError, "payload_length mismatch"):
            decode_message(self._encode_raw(tampered_header + raw[HEADER_SIZE:]))

    def test_unknown_enums(self):
        with self.assertRaisesRegex(DecodingError, "Unknown source agent code"):
            decode_compact_payload(bytes((99, 2, 1)) + b"x")
        with self.assertRaisesRegex(DecodingError, "Unknown destination agent code"):
            decode_compact_payload(bytes((1, 99, 1)) + b"x")
        with self.assertRaisesRegex(DecodingError, "Unknown instruction code"):
            decode_compact_payload(bytes((1, 2, 99)) + b"x")


class AdaptiveCodecTests(unittest.TestCase):
    def test_alias_warmup_and_decode(self):
        codec = AdaptiveCodec(warmup_hits=3)
        self.assertEqual(codec.encode("PING")[0], 0xA1)
        self.assertEqual(codec.encode("PING")[0], 0xA1)
        alias_payload = codec.encode("PING")
        self.assertEqual(alias_payload[0], 0xA0)
        self.assertEqual(codec.decode(alias_payload), "PING")

    def test_encode_decode_raw_mode(self):
        codec = AdaptiveCodec()
        payload = codec.encode("HELLO")
        self.assertEqual(payload[0], 0xA1)
        self.assertEqual(codec.decode(payload), "HELLO")


class StreamingTests(unittest.TestCase):
    def test_iter_stream_text_reassembles_chunks(self):
        message = "abcdefghij"
        frames = encode_stream(message, chunk_size=3)
        self.assertEqual("".join(iter_stream_text(frames)), message)


if __name__ == "__main__":
    unittest.main()
