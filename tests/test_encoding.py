import base64
import struct
import unittest

from logorrhythm.encoding import decode_message, encode_message
from logorrhythm.exceptions import DecodingError
from logorrhythm.spec import HEADER_SIZE, MessageType


class EncodingTests(unittest.TestCase):
    def _decode_raw(self, text: str) -> bytes:
        pad = "=" * ((4 - len(text) % 4) % 4)
        return base64.urlsafe_b64decode((text + pad).encode("ascii"))

    def _encode_raw(self, blob: bytes) -> str:
        return base64.urlsafe_b64encode(blob).rstrip(b"=").decode("ascii")

    def test_round_trip_handoff(self):
        payload = b'{"handoff":"agent2"}'
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=payload)
        decoded = decode_message(encoded)
        self.assertEqual(decoded.message_type, MessageType.HANDOFF)
        self.assertEqual(decoded.payload, payload)


    def test_reject_invalid_base64url_transport(self):
        with self.assertRaisesRegex(DecodingError, "Invalid base64url transport"):
            decode_message("@@@")

    def test_reject_invalid_checksum(self):
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=b"abc")
        raw = bytearray(self._decode_raw(encoded))
        raw[HEADER_SIZE] ^= 0x01
        with self.assertRaisesRegex(DecodingError, "CRC32"):
            decode_message(self._encode_raw(bytes(raw)))

    def test_reject_payload_length_mismatch(self):
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=b"abc")
        raw = self._decode_raw(encoded)
        version, mt, flags, caps, plen, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags, caps, plen + 1, crc)
        tampered = tampered_header + raw[HEADER_SIZE:]
        with self.assertRaisesRegex(DecodingError, "payload_length mismatch"):
            decode_message(self._encode_raw(tampered))

    def test_reject_oversized_message(self):
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=b"abc")
        with self.assertRaisesRegex(DecodingError, "max_message_bytes"):
            decode_message(encoded, max_message_bytes=8)

    def test_reject_unsupported_version(self):
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=b"abc")
        raw = bytearray(self._decode_raw(encoded))
        raw[0] = 9
        with self.assertRaisesRegex(DecodingError, "Unsupported protocol version"):
            decode_message(self._encode_raw(bytes(raw)))

    def test_reject_reserved_capability_bits_non_zero(self):
        encoded = encode_message(message_type=MessageType.HANDOFF, payload=b"abc")
        raw = self._decode_raw(encoded)
        version, mt, flags, caps, plen, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags, caps | 0x8000, plen, crc)
        tampered = tampered_header + raw[HEADER_SIZE:]
        with self.assertRaisesRegex(DecodingError, "Reserved capability bits"):
            decode_message(self._encode_raw(tampered))


if __name__ == "__main__":
    unittest.main()
