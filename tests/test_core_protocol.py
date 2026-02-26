import json
import unittest

from logorrhythm import Session
from logorrhythm.core.errors import DecodingError, HandshakeError
from logorrhythm.core.frame import decode_uvarint, parse_frame
from logorrhythm.core.schema import canonical_bytes, fingerprint, normalize_schema
from logorrhythm.core.session import (
    ACK,
    FLAG_DELTA,
    FLAG_VALUE_REF,
    HELLO,
    MODE_OPCODE,
    MODE_RAW,
    NACK,
    OPCODE_MESSAGE,
    RAW_MESSAGE,
    SCHEMA_FINGERPRINT,
    SCHEMA_TRANSFER,
    SessionConfig,
)


SCHEMA_A = {
    "message_types": {"TASK": "auto", "RESULT": "auto"},
    "fields": {"id": "auto", "cmd": "auto", "target": "auto", "n": "auto", "meta": "auto"},
    "field_types": {"id": "uvarint", "cmd": "str", "target": "str", "n": "svarint", "meta": "map"},
}

SCHEMA_B = {
    "field_types": {"target": "str", "cmd": "str", "n": "svarint", "id": "uvarint", "meta": "map"},
    "fields": {"target": "auto", "n": "auto", "cmd": "auto", "id": "auto", "meta": "auto"},
    "message_types": {"RESULT": "auto", "TASK": "auto"},
}


class ProtocolTests(unittest.TestCase):
    def _handshake_pair(self, client: Session, server: Session) -> None:
        outbound = [client.initiate_handshake()]
        turn_server = True
        while outbound:
            next_outbound = []
            for frame in outbound:
                responses = server.receive(frame) if turn_server else client.receive(frame)
                next_outbound.extend(responses)
            outbound = next_outbound
            turn_server = not turn_server

    # A) SCHEMA TESTS
    def test_schema_canonicalization_identical_bytes(self):
        self.assertEqual(canonical_bytes(SCHEMA_A), canonical_bytes(SCHEMA_B))

    def test_schema_fingerprint_stable(self):
        fp1 = fingerprint(SCHEMA_A)
        fp2 = fingerprint(SCHEMA_A)
        fresh = Session(schema=SCHEMA_A, role="client").schema_fp
        self.assertEqual(fp1, fp2)
        self.assertEqual(fp1, fresh)

    def test_schema_fingerprint_changes_when_schema_changes(self):
        changed = {
            **SCHEMA_A,
            "fields": {**SCHEMA_A["fields"], "new_field": "auto"},
            "field_types": {**SCHEMA_A["field_types"], "new_field": "str"},
        }
        self.assertNotEqual(fingerprint(SCHEMA_A), fingerprint(changed))

    def test_schema_transfer_round_trip(self):
        cbytes = canonical_bytes(SCHEMA_A)
        transferred = json.loads(cbytes.decode("utf-8"))
        self.assertEqual(normalize_schema(SCHEMA_A), normalize_schema(transferred))

    # B) HANDSHAKE TESTS
    def test_matching_fingerprint_ack_to_opcode_mode(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema=SCHEMA_A, role="server")
        self._handshake_pair(a, b)
        self.assertEqual(a.mode, MODE_OPCODE)
        self.assertEqual(b.mode, MODE_OPCODE)

    def test_mismatch_schema_transfer_ack_switch(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema={"message_types": {"OTHER": 1}, "fields": {"x": 1}}, role="server")
        self._handshake_pair(a, b)
        self.assertTrue(a.handshake_complete)
        self.assertTrue(b.handshake_complete)

    def test_mismatch_strict_mode_nack_and_remain_raw(self):
        strict = SessionConfig(strict_mode=True, allow_schema_transfer=False)
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema={"message_types": {"OTHER": 1}, "fields": {"x": 1}}, role="server", config=strict)
        out = a.initiate_handshake()
        responses = b.receive(out)
        self.assertEqual(parse_frame(responses[0])[0], NACK)
        a.receive(responses[0])
        self.assertEqual(b.mode, MODE_RAW)
        self.assertEqual(a.mode, MODE_HANDSHAKE := "HANDSHAKE")

    def test_repeated_hello_is_idempotent(self):
        b = Session(schema=SCHEMA_A, role="server")
        self.assertEqual(b._handle_frame(HELLO, b""), [])
        self.assertEqual(b._handle_frame(HELLO, b""), [])
        self.assertFalse(b.handshake_complete)

    def test_encode_before_handshake_uses_raw_mode(self):
        s = Session(schema=SCHEMA_A, role="client")
        wire = s.encode("TASK", {"id": 1, "cmd": "scan", "target": "x", "n": 1, "meta": {}})
        frame_type, _ = parse_frame(wire)
        self.assertEqual(frame_type, RAW_MESSAGE)

    # C) OPCODE ENCODING TESTS
    def test_opcode_encode_decode_roundtrip_small_message(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema=SCHEMA_A, role="server")
        a.mode = b.mode = MODE_OPCODE
        wire = a.encode("TASK", {"id": 1})
        msg = b.decode(wire)
        self.assertEqual(msg["fields"]["id"], 1)

    def test_opcode_roundtrip_multifield_nested_and_large_int_signed(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema=SCHEMA_A, role="server")
        a.mode = b.mode = MODE_OPCODE
        payload = {"id": 99, "cmd": "scan", "target": "node", "n": -444444, "meta": {"nested": [1, {"a": True}]}}
        wire = a.encode("TASK", payload)
        decoded = b.decode(wire)
        self.assertEqual(decoded["fields"], payload)

    def test_field_order_does_not_change_wire_output(self):
        s1 = Session(schema=SCHEMA_A, role="client", config=SessionConfig(learning_threshold=99))
        s2 = Session(schema=SCHEMA_A, role="client", config=SessionConfig(learning_threshold=99))
        s1.mode = s2.mode = MODE_OPCODE
        p1 = {"id": 1, "cmd": "scan", "target": "x", "n": 1, "meta": {"a": 1}}
        p2 = {"meta": {"a": 1}, "target": "x", "n": 1, "cmd": "scan", "id": 1}
        self.assertEqual(s1.encode("TASK", p1), s2.encode("TASK", p2))

    def test_unknown_opcode_raises_deterministic_error(self):
        s = Session(schema=SCHEMA_A, role="client")
        s.mode = MODE_OPCODE
        with self.assertRaisesRegex(KeyError, "MISSING"):
            s.encode("MISSING", {"id": 1})

    def test_unknown_field_raises_deterministic_error(self):
        s = Session(schema=SCHEMA_A, role="client")
        s.mode = MODE_OPCODE
        with self.assertRaisesRegex(KeyError, "unknown"):
            s.encode("TASK", {"unknown": 1})

    # D) VALUE TABLE TESTS

    def test_nested_values_not_learned_in_value_table(self):
        s = Session(schema=SCHEMA_A, role="client")
        s.mode = MODE_OPCODE
        nested = {"k": [1, {"a": True}]}
        s.encode("TASK", {"id": 1, "cmd": "scan", "target": "x", "n": 1, "meta": nested})
        self.assertIsNone(s.value_table.get_id(nested))

    def test_repeated_literal_becomes_value_ref_after_threshold(self):
        cfg = SessionConfig(learning_threshold=2)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        m1 = s.encode("TASK", {"id": 1, "cmd": "scan", "target": "t", "n": 0, "meta": {}})
        m2 = s.encode("TASK", {"id": 2, "cmd": "scan", "target": "t", "n": 1, "meta": {}})
        self.assertNotEqual(m1, m2)
        self.assertIsNotNone(s.value_table.get_id("scan"))

    def test_learning_threshold_respected(self):
        cfg = SessionConfig(learning_threshold=3)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        for i in range(2):
            s.encode("TASK", {"id": i, "cmd": "repeat", "target": "x", "n": i, "meta": {}})
        self.assertIsNone(s.value_table.get_id("repeat"))
        s.encode("TASK", {"id": 3, "cmd": "repeat", "target": "x", "n": 3, "meta": {}})
        self.assertIsNotNone(s.value_table.get_id("repeat"))

    def test_lru_cap_enforced_and_unique_stream_bounded(self):
        cfg = SessionConfig(learning_threshold=1, value_table_max_entries=64)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        total_wire = total_raw = 0
        for i in range(1000):
            fields = {"id": i, "cmd": f"u{i}", "target": f"t{i}", "n": i, "meta": {"i": i}}
            total_wire += len(s.encode("TASK", fields))
            total_raw += len(s._encode_raw("TASK", fields))
        self.assertLessEqual(len(s.value_table.value_to_id), 64)
        self.assertLess(total_wire / total_raw, 1.5)

    def test_session_reset_clears_value_table(self):
        s = Session(schema=SCHEMA_A, role="client")
        s.mode = MODE_OPCODE
        s.encode("TASK", {"id": 1, "cmd": "scan", "target": "x", "n": 1, "meta": {}})
        s.reset()
        self.assertFalse(s.value_table.value_to_id)

    # E) DELTA ENCODING TESTS
    def test_first_value_absolute_then_delta(self):
        cfg = SessionConfig(learning_threshold=99)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        first = s.encode("TASK", {"id": 1, "cmd": "a", "target": "x", "n": 100, "meta": {}})
        second = s.encode("TASK", {"id": 2, "cmd": "a", "target": "x", "n": 101, "meta": {}})
        self.assertLess(len(second), len(first))

    def test_negative_deltas_correct(self):
        cfg = SessionConfig(learning_threshold=99)
        a = Session(schema=SCHEMA_A, role="client", config=cfg)
        b = Session(schema=SCHEMA_A, role="server", config=cfg)
        a.mode = b.mode = MODE_OPCODE
        b.decode(a.encode("TASK", {"id": 1, "cmd": "x", "target": "t", "n": 10, "meta": {}}))
        out = b.decode(a.encode("TASK", {"id": 2, "cmd": "x", "target": "t", "n": 7, "meta": {}}))
        self.assertEqual(out["fields"]["n"], 7)

    def test_switching_fields_does_not_leak_delta_state(self):
        cfg = SessionConfig(learning_threshold=99)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        w1 = s.encode("TASK", {"id": 1, "cmd": "x", "target": "t", "n": 10, "meta": {}})
        w2 = s.encode("TASK", {"id": 200, "cmd": "x", "target": "t", "n": 11, "meta": {}})
        self.assertNotEqual(w1, w2)

    def test_large_deltas_fallback_safely(self):
        cfg = SessionConfig(learning_threshold=99)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        s.encode("TASK", {"id": 1, "cmd": "x", "target": "t", "n": 0, "meta": {}})
        small_delta = s.encode("TASK", {"id": 2, "cmd": "x", "target": "t", "n": 1, "meta": {}})
        large_delta = s.encode("TASK", {"id": 3, "cmd": "x", "target": "t", "n": 1000, "meta": {}})
        self.assertGreater(len(large_delta), len(small_delta))

    # F) WORST-CASE SAFETY TESTS
    def test_corrupted_frame_raises(self):
        s = Session(schema=SCHEMA_A, role="server")
        with self.assertRaises(DecodingError):
            s.decode(bytes([OPCODE_MESSAGE, 2, 0xFF]))

    def test_partial_frame_decode_safe(self):
        s = Session(schema=SCHEMA_A, role="server")
        with self.assertRaises(DecodingError):
            s.receive(bytes([ACK, 4, 1]))

    def test_maliciously_large_varint_rejected(self):
        with self.assertRaises(DecodingError):
            decode_uvarint(bytes([0x80] * 11 + [0x01]), 0)

    # G) DETERMINISM TESTS
    def test_same_inputs_across_runs_identical_wire(self):
        p = {"id": 1, "cmd": "scan", "target": "x", "n": 9, "meta": {"k": [1, 2]}}
        a1 = Session(schema=SCHEMA_A, role="client")
        a2 = Session(schema=SCHEMA_A, role="client")
        a1.mode = a2.mode = MODE_OPCODE
        self.assertEqual(a1.encode("TASK", p), a2.encode("TASK", p))

    def test_value_table_ids_stable(self):
        def learn_ids() -> tuple[int | None, int | None]:
            s = Session(schema=SCHEMA_A, role="client", config=SessionConfig(learning_threshold=1))
            s.mode = MODE_OPCODE
            s.encode("TASK", {"id": 1, "cmd": "alpha", "target": "x", "n": 1, "meta": {}})
            s.encode("TASK", {"id": 2, "cmd": "beta", "target": "x", "n": 2, "meta": {}})
            return s.value_table.get_id("alpha"), s.value_table.get_id("beta")

        first = learn_ids()
        second = learn_ids()
        self.assertEqual(first, second)

    # H) MEMORY / STATE TESTS
    def test_value_table_size_bounded_over_long_session(self):
        s = Session(schema=SCHEMA_A, role="client", config=SessionConfig(learning_threshold=1, value_table_max_entries=128))
        s.mode = MODE_OPCODE
        for i in range(10000):
            s.encode("TASK", {"id": i, "cmd": f"c{i}", "target": f"t{i}", "n": i, "meta": {"i": i}})
        self.assertLessEqual(len(s.value_table.value_to_id), 128)

    def test_handshake_schema_fingerprint_mismatch_raises(self):
        s = Session(schema=SCHEMA_A, role="server")
        s.remote_fingerprint = "00" * 32
        with self.assertRaises(HandshakeError):
            s._handle_frame(SCHEMA_TRANSFER, canonical_bytes(SCHEMA_A))


if __name__ == "__main__":
    unittest.main()
