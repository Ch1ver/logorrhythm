import base64
import struct
import unittest

from logorrhythm.encoding import (
    decode_compact_payload,
    decode_message,
    encode_compact_payload,
    encode_message,
)
from logorrhythm.exceptions import DecodingError
from logorrhythm.spec import HEADER_SIZE, AgentCode, InstructionCode, MessageType


class EncodingTests(unittest.TestCase):
    def _decode_raw(self, text: str) -> bytes:
        pad = "=" * ((4 - len(text) % 4) % 4)
        return base64.urlsafe_b64decode((text + pad).encode("ascii"))

    def _encode_raw(self, blob: bytes) -> str:
        return base64.urlsafe_b64encode(blob).rstrip(b"=").decode("ascii")

    def test_round_trip_agent_message(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="status?",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        decoded = decode_message(encoded)
        compact = decode_compact_payload(decoded.payload)
        self.assertEqual(decoded.message_type, MessageType.AGENT)
        self.assertEqual(compact.src, AgentCode.A1)
        self.assertEqual(compact.dst, AgentCode.A2)
        self.assertEqual(compact.instruction, InstructionCode.HANDOFF)
        self.assertEqual(compact.task, "status?")



    def test_binary_transport_round_trip(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="status?",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload)
        self.assertIsInstance(encoded, bytes)
        decoded = decode_message(encoded)
        self.assertEqual(decode_compact_payload(decoded.payload).task, "status?")

    def test_reject_non_enum_compact_payload_fields(self):
        with self.assertRaisesRegex(Exception, "src must be an AgentCode"):
            encode_compact_payload(src=1, dst=AgentCode.A2, instruction=InstructionCode.HANDOFF, task="x")
        with self.assertRaisesRegex(Exception, "dst must be an AgentCode"):
            encode_compact_payload(src=AgentCode.A1, dst=2, instruction=InstructionCode.HANDOFF, task="x")
        with self.assertRaisesRegex(Exception, "instruction must be an InstructionCode"):
            encode_compact_payload(src=AgentCode.A1, dst=AgentCode.A2, instruction=1, task="x")

    def test_reject_invalid_base64url_transport(self):
        with self.assertRaisesRegex(DecodingError, "Invalid base64url transport"):
            decode_message("@@@")

    def test_reject_invalid_checksum(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        raw = bytearray(self._decode_raw(encoded))
        raw[HEADER_SIZE] ^= 0x01
        with self.assertRaisesRegex(DecodingError, "CRC32"):
            decode_message(self._encode_raw(bytes(raw)))

    def test_reject_payload_length_mismatch(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        raw = self._decode_raw(encoded)
        version, mt, flags, caps, plen, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags, caps, plen + 1, crc)
        tampered = tampered_header + raw[HEADER_SIZE:]
        with self.assertRaisesRegex(DecodingError, "payload_length mismatch"):
            decode_message(self._encode_raw(tampered))

    def test_reject_oversized_message(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        with self.assertRaisesRegex(DecodingError, "max_message_bytes"):
            decode_message(encoded, max_message_bytes=8)

    def test_reject_unsupported_version(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        raw = bytearray(self._decode_raw(encoded))
        raw[0] = 9
        with self.assertRaisesRegex(DecodingError, "Unsupported protocol version"):
            decode_message(self._encode_raw(bytes(raw)))

    def test_reject_reserved_capability_bits_non_zero(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        raw = self._decode_raw(encoded)
        version, mt, flags, caps, plen, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags, caps | 0x8000, plen, crc)
        tampered = tampered_header + raw[HEADER_SIZE:]
        with self.assertRaisesRegex(DecodingError, "Reserved capability bits"):
            decode_message(self._encode_raw(tampered))

    def test_reject_unknown_instruction_code(self):
        bad_payload = bytes((1, 2, 255)) + b"task"
        encoded = encode_message(message_type=MessageType.AGENT, payload=bad_payload)
        with self.assertRaisesRegex(DecodingError, "Unknown instruction code"):
            decode_message(encoded)

    def test_reject_reserved_flag_bits_non_zero(self):
        payload = encode_compact_payload(
            src=AgentCode.A1,
            dst=AgentCode.A2,
            instruction=InstructionCode.HANDOFF,
            task="abc",
        )
        encoded = encode_message(message_type=MessageType.AGENT, payload=payload, transport_base64=True)
        raw = self._decode_raw(encoded)
        version, mt, flags, caps, plen, crc = struct.unpack(">BBBHHI", raw[:HEADER_SIZE])
        tampered_header = struct.pack(">BBBHHI", version, mt, flags | 0x80, caps, plen, crc)
        tampered = tampered_header + raw[HEADER_SIZE:]
        with self.assertRaisesRegex(DecodingError, "Reserved flag bits"):
            decode_message(self._encode_raw(tampered))

    def test_reject_oversized_encoded_transport_before_decode(self):
        with self.assertRaisesRegex(DecodingError, "Encoded transport exceeds"):
            decode_message("A" * 17, max_message_bytes=12)


if __name__ == "__main__":
    unittest.main()
