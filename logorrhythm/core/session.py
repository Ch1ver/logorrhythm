"""Session state machine and opcode-mode codec."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .errors import DecodingError, HandshakeError
from .frame import (
    decode_bytes,
    decode_str,
    decode_svarint,
    decode_uvarint,
    encode_bytes,
    encode_str,
    encode_svarint,
    encode_uvarint,
    make_frame,
    parse_frame,
)
from .schema import canonical_bytes, fingerprint, normalize_schema
from .tables import NameTable, ValueTable

HELLO = 1
SCHEMA_FINGERPRINT = 2
SCHEMA_TRANSFER = 3
ACK = 4
NACK = 5
MODE_SWITCH = 6
OPCODE_MESSAGE = 16
RAW_MESSAGE = 17
JSON_BRIDGE_MESSAGE = 18

MODE_HANDSHAKE = "HANDSHAKE"
MODE_OPCODE = "OPCODE_MODE"
MODE_RAW = "RAW"
MODE_JSON_BRIDGE = "JSON_BRIDGE"

FLAG_VALUE_REF = 0x1
FLAG_DELTA = 0x2

TYPE_UVARINT = 1
TYPE_SVARINT = 2
TYPE_BYTES = 3
TYPE_STR = 4
TYPE_BOOL = 5
TYPE_JSON = 6


@dataclass
class SessionConfig:
    strict_mode: bool = False
    allow_schema_transfer: bool = True
    value_table_max_entries: int = 4096
    learning_threshold: int = 2
    learn_fields: set[str] | None = None


class Session:
    def __init__(self, schema: dict, role: str, config: SessionConfig | None = None):
        self.role = role
        self.config = config or SessionConfig()
        self.schema = normalize_schema(schema)
        self.schema_fp = fingerprint(self.schema)
        self.schema_cache: dict[str, dict] = {self.schema_fp: self.schema}
        self.mode = MODE_HANDSHAKE
        self.handshake_complete = False
        self.remote_fingerprint: str | None = None

        self.value_table = ValueTable(
            max_entries=self.config.value_table_max_entries,
            learning_threshold=self.config.learning_threshold,
        )
        self.last_values: dict[int, int] = {}
        self._activate_schema(self.schema)

    def _activate_schema(self, schema: dict) -> None:
        self.opcodes = NameTable(schema["message_types"])
        self.fields = NameTable(schema["fields"])
        self.field_types = schema.get("field_types", {})
        self.value_table.reset()
        enum_values: list[object] = []
        for _field, values in schema.get("enums", {}).items():
            enum_values.extend(values)
        if enum_values:
            self.value_table.preload(enum_values)
        self.last_values.clear()

    def initiate_handshake(self) -> bytes:
        cap_flags = 0b00000011
        return b"".join([
            make_frame(HELLO, encode_uvarint(cap_flags)),
            make_frame(SCHEMA_FINGERPRINT, bytes.fromhex(self.schema_fp)),
        ])

    def receive(self, in_bytes: bytes) -> list[bytes]:
        outputs: list[bytes] = []
        cursor = 0
        while cursor < len(in_bytes):
            if cursor + 1 > len(in_bytes):
                raise DecodingError("truncated frame header")
            frame_type = in_bytes[cursor]
            ln, next_pos = decode_uvarint(in_bytes, cursor + 1)
            end = next_pos + ln
            if end > len(in_bytes):
                raise DecodingError("truncated frame payload")
            payload = in_bytes[next_pos:end]
            cursor = end
            outputs.extend(self._handle_frame(frame_type, payload))
        return outputs

    def _handle_frame(self, frame_type: int, payload: bytes) -> list[bytes]:
        if frame_type == HELLO:
            return []
        if frame_type == SCHEMA_FINGERPRINT:
            remote_fp = payload.hex()
            self.remote_fingerprint = remote_fp
            if remote_fp in self.schema_cache:
                self._activate_schema(self.schema_cache[remote_fp])
                return [make_frame(ACK, b"")]
            if self.config.strict_mode and not self.config.allow_schema_transfer:
                self.mode = MODE_RAW
                return [make_frame(NACK, b"strict")]
            return [make_frame(NACK, b"schema")]
        if frame_type == SCHEMA_TRANSFER:
            received = json.loads(payload.decode("utf-8"))
            fp = fingerprint(received)
            if self.remote_fingerprint and fp != self.remote_fingerprint:
                raise HandshakeError("schema fingerprint mismatch")
            normalized = normalize_schema(received)
            self.schema_cache[fp] = normalized
            self.remote_fingerprint = fp
            self._activate_schema(normalized)
            return [make_frame(ACK, b"")]
        if frame_type == ACK:
            if self.mode == MODE_HANDSHAKE:
                self.mode = MODE_OPCODE
                self.handshake_complete = True
                return [make_frame(MODE_SWITCH, b"")]
            return []
        if frame_type == NACK:
            if not self.config.allow_schema_transfer:
                self.mode = MODE_RAW
                return []
            return [make_frame(SCHEMA_TRANSFER, canonical_bytes(self.schema))]
        if frame_type == MODE_SWITCH:
            self.mode = MODE_OPCODE
            self.handshake_complete = True
            return []
        return []

    def encode(self, opcode: str, fields: dict[str, object]) -> bytes:
        if self.mode != MODE_OPCODE:
            return self._encode_raw(opcode, fields)
        opcode_id = self.opcodes.name_to_id[opcode]
        body = bytearray()
        body.extend(encode_uvarint(opcode_id))
        body.extend(encode_uvarint(len(fields)))
        for name in sorted(fields, key=lambda n: self.fields.name_to_id[n]):
            field_id = self.fields.name_to_id[name]
            val = fields[name]
            is_int_delta_eligible = isinstance(val, int) and not isinstance(val, bool)
            flags = 0
            payload = b""
            ref_id = self.value_table.get_id(val)
            if ref_id is not None:
                flags |= FLAG_VALUE_REF
                payload = encode_uvarint(ref_id)
            elif is_int_delta_eligible and field_id in self.last_values:
                delta = val - self.last_values[field_id]
                if -63 <= delta <= 63:
                    flags |= FLAG_DELTA
                    payload = encode_svarint(delta)
                else:
                    payload = self._encode_typed_literal(name, val)
            else:
                payload = self._encode_typed_literal(name, val)
            body.extend(encode_uvarint(field_id))
            body.extend(encode_uvarint(flags))
            body.extend(payload)
            self._learn_value(name, val)
            if is_int_delta_eligible:
                self.last_values[field_id] = val
        return make_frame(OPCODE_MESSAGE, bytes(body))

    def decode(self, msg: bytes) -> dict:
        frame_type, payload = parse_frame(msg)
        if frame_type == RAW_MESSAGE:
            return json.loads(payload.decode("utf-8"))
        if frame_type != OPCODE_MESSAGE:
            raise DecodingError("unsupported frame type")
        pos = 0
        opcode_id, pos = decode_uvarint(payload, pos)
        field_count, pos = decode_uvarint(payload, pos)
        fields: dict[str, object] = {}
        opcode = self.opcodes.id_to_name[opcode_id]
        for _ in range(field_count):
            field_id, pos = decode_uvarint(payload, pos)
            flags, pos = decode_uvarint(payload, pos)
            name = self.fields.id_to_name[field_id]
            if flags & FLAG_VALUE_REF:
                ref_id, pos = decode_uvarint(payload, pos)
                val = self.value_table.get_value(ref_id)
            elif flags & FLAG_DELTA:
                delta, pos = decode_svarint(payload, pos)
                prev = self.last_values.get(field_id, 0)
                val = prev + delta
            else:
                val, pos = self._decode_typed_literal(name, payload, pos)
            fields[name] = val
            self._learn_value(name, val)
            if isinstance(val, int) and not isinstance(val, bool):
                self.last_values[field_id] = val
        return {"opcode": opcode, "fields": fields}

    def _encode_raw(self, opcode: str, fields: dict[str, object]) -> bytes:
        return make_frame(
            RAW_MESSAGE,
            json.dumps({"opcode": opcode, "fields": fields}, separators=(",", ":")).encode("utf-8"),
        )

    def _type_code_for(self, name: str, value: object) -> int:
        declared = self.field_types.get(name)
        if declared == "uvarint":
            return TYPE_UVARINT
        if declared == "svarint":
            return TYPE_SVARINT
        if declared == "bytes":
            return TYPE_BYTES
        if declared == "str":
            return TYPE_STR
        if declared == "bool":
            return TYPE_BOOL
        if isinstance(value, bool):
            return TYPE_BOOL
        if isinstance(value, int):
            return TYPE_SVARINT if value < 0 else TYPE_UVARINT
        if isinstance(value, bytes):
            return TYPE_BYTES
        if isinstance(value, str):
            return TYPE_STR
        return TYPE_JSON

    def _encode_typed_literal(self, name: str, value: object) -> bytes:
        t = self._type_code_for(name, value)
        out = bytearray(encode_uvarint(t))
        if t == TYPE_UVARINT:
            out.extend(encode_uvarint(int(value)))
        elif t == TYPE_SVARINT:
            out.extend(encode_svarint(int(value)))
        elif t == TYPE_BYTES:
            out.extend(encode_bytes(value))
        elif t == TYPE_STR:
            out.extend(encode_str(value))
        elif t == TYPE_BOOL:
            out.extend(encode_uvarint(1 if value else 0))
        else:
            out.extend(encode_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8")))
        return bytes(out)

    def _decode_typed_literal(self, name: str, payload: bytes, pos: int) -> tuple[object, int]:
        t, pos = decode_uvarint(payload, pos)
        if t == TYPE_UVARINT:
            return decode_uvarint(payload, pos)
        if t == TYPE_SVARINT:
            return decode_svarint(payload, pos)
        if t == TYPE_BYTES:
            return decode_bytes(payload, pos)
        if t == TYPE_STR:
            return decode_str(payload, pos)
        if t == TYPE_BOOL:
            b, pos = decode_uvarint(payload, pos)
            return bool(b), pos
        blob, pos = decode_bytes(payload, pos)
        return json.loads(blob.decode("utf-8")), pos

    def _learn_value(self, field_name: str, value: object) -> None:
        allow = self.config.learn_fields is None or field_name in self.config.learn_fields
        self.value_table.maybe_learn(value, allow=allow)

    def reset(self) -> None:
        self.mode = MODE_HANDSHAKE
        self.handshake_complete = False
        self.remote_fingerprint = None
        self._activate_schema(self.schema)
