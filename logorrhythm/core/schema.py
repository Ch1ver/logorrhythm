"""Schema canonicalization and fingerprinting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .errors import SchemaError

_ALLOWED_TYPES = {"uvarint", "svarint", "bytes", "str", "bool", "list", "map"}


def _assign_ids(mapping: dict[str, int | str], label: str) -> dict[str, int]:
    explicit = {k: int(v) for k, v in mapping.items() if v != "auto"}
    used = set(explicit.values())
    next_id = 1
    assigned = {}
    for name in sorted(mapping):
        raw = mapping[name]
        if raw == "auto":
            while next_id in used:
                next_id += 1
            assigned[name] = next_id
            used.add(next_id)
            next_id += 1
        else:
            assigned[name] = int(raw)
    if len(set(assigned.values())) != len(assigned):
        raise SchemaError(f"duplicate {label} ids")
    return assigned


def normalize_schema(schema: dict) -> dict:
    if "message_types" not in schema or "fields" not in schema:
        raise SchemaError("schema requires message_types and fields")
    msg_types = _assign_ids(schema["message_types"], "opcode")
    fields = _assign_ids(schema["fields"], "field")
    field_types = schema.get("field_types", {})
    normalized_types = {}
    for field in sorted(field_types):
        ftype = field_types[field]
        if ftype not in _ALLOWED_TYPES:
            raise SchemaError(f"unsupported field type: {ftype}")
        normalized_types[field] = ftype
    enums = schema.get("enums", {})
    normalized_enums = {
        key: sorted(list(values))
        for key, values in sorted(enums.items(), key=lambda kv: kv[0])
    }
    return {
        "message_types": {k: msg_types[k] for k in sorted(msg_types)},
        "fields": {k: fields[k] for k in sorted(fields)},
        "field_types": normalized_types,
        "enums": normalized_enums,
    }


def canonical_bytes(schema: dict) -> bytes:
    normalized = normalize_schema(schema)
    return json.dumps(normalized, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def fingerprint(schema: dict) -> str:
    return hashlib.sha256(canonical_bytes(schema)).hexdigest()


def load_schema(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
