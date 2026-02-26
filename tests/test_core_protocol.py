import unittest

from logorrhythm import Session
from logorrhythm.core.schema import canonical_bytes, fingerprint
from logorrhythm.core.session import MODE_OPCODE, SessionConfig


SCHEMA_A = {
    "message_types": {"TASK": "auto", "RESULT": "auto"},
    "fields": {"id": "auto", "cmd": "auto", "target": "auto", "n": "auto"},
    "field_types": {"id": "uvarint", "cmd": "str", "target": "str", "n": "uvarint"},
}

SCHEMA_B = {
    "field_types": {"target": "str", "cmd": "str", "n": "uvarint", "id": "uvarint"},
    "fields": {"target": "auto", "n": "auto", "cmd": "auto", "id": "auto"},
    "message_types": {"RESULT": "auto", "TASK": "auto"},
}


class ProtocolTests(unittest.TestCase):
    def _handshake_pair(self, a, b):
        out = a.initiate_handshake()
        responses = b.receive(out)
        while responses:
            next_responses = []
            for frame in responses:
                next_responses.extend(a.receive(frame))
            responses = []
            for frame in next_responses:
                responses.extend(b.receive(frame))

    def test_schema_canonicalization_stable(self):
        self.assertEqual(canonical_bytes(SCHEMA_A), canonical_bytes(SCHEMA_B))

    def test_fingerprint_consistency(self):
        self.assertEqual(fingerprint(SCHEMA_A), fingerprint(SCHEMA_B))

    def test_handshake_success_matching_fingerprint(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema=SCHEMA_A, role="server")
        self._handshake_pair(a, b)
        self.assertEqual(a.mode, MODE_OPCODE)
        self.assertEqual(b.mode, MODE_OPCODE)

    def test_handshake_success_schema_transfer(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema={**SCHEMA_A, "message_types": {"OTHER": 1}, "fields": {"x": 1}}, role="server")
        self._handshake_pair(a, b)
        self.assertEqual(a.mode, MODE_OPCODE)
        self.assertEqual(b.mode, MODE_OPCODE)

    def test_opcode_mode_roundtrip(self):
        a = Session(schema=SCHEMA_A, role="client")
        b = Session(schema=SCHEMA_A, role="server")
        a.mode = b.mode = MODE_OPCODE
        wire = a.encode("TASK", {"id": 7, "cmd": "scan", "target": "x", "n": 9})
        msg = b.decode(wire)
        self.assertEqual(msg["opcode"], "TASK")
        self.assertEqual(msg["fields"]["cmd"], "scan")

    def test_value_table_learning_threshold_behavior(self):
        cfg = SessionConfig(learning_threshold=3)
        a = Session(schema=SCHEMA_A, role="client", config=cfg)
        b = Session(schema=SCHEMA_A, role="server", config=cfg)
        a.mode = b.mode = MODE_OPCODE
        m1 = a.encode("TASK", {"id": 1, "cmd": "scan", "target": "x", "n": 1})
        m2 = a.encode("TASK", {"id": 2, "cmd": "scan", "target": "x", "n": 1})
        m3 = a.encode("TASK", {"id": 3, "cmd": "scan", "target": "x", "n": 1})
        m4 = a.encode("TASK", {"id": 4, "cmd": "scan", "target": "x", "n": 1})
        self.assertGreaterEqual(len(m1), len(m2))
        self.assertGreater(len(m3), len(m4))
        b.decode(m1)
        b.decode(m2)
        b.decode(m3)
        b.decode(m4)

    def test_delta_encoding_correctness(self):
        cfg = SessionConfig(learning_threshold=10)
        a = Session(schema=SCHEMA_A, role="client", config=cfg)
        b = Session(schema=SCHEMA_A, role="server", config=cfg)
        a.mode = b.mode = MODE_OPCODE
        m1 = a.encode("TASK", {"id": 10, "cmd": "scan", "target": "x", "n": 100})
        m2 = a.encode("TASK", {"id": 11, "cmd": "scan", "target": "x", "n": 103})
        self.assertLess(len(m2), len(m1))
        b.decode(m1)
        d2 = b.decode(m2)
        self.assertEqual(d2["fields"]["n"], 103)

    def test_unique_stream_bounded_regression(self):
        cfg = SessionConfig(learning_threshold=3)
        s = Session(schema=SCHEMA_A, role="client", config=cfg)
        s.mode = MODE_OPCODE
        total_wire = total_raw = 0
        for i in range(400):
            fields = {"id": i, "cmd": f"u{i}", "target": f"t{i}", "n": i}
            total_wire += len(s.encode("TASK", fields))
            total_raw += len(s._encode_raw("TASK", fields))
        self.assertLess(total_wire, int(total_raw * 1.35))

    def test_session_reset_semantics(self):
        s = Session(schema=SCHEMA_A, role="client")
        s.mode = MODE_OPCODE
        s.encode("TASK", {"id": 1, "cmd": "scan", "target": "x", "n": 1})
        self.assertTrue(s.last_values)
        self.assertTrue(s.value_table._seen)
        s.reset()
        self.assertEqual(s.mode, "HANDSHAKE")
        self.assertFalse(s.last_values)
        self.assertFalse(s.value_table.value_to_id)


if __name__ == "__main__":
    unittest.main()
