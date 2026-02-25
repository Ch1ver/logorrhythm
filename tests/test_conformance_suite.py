import json
import unittest

from logorrhythm.adaptive import AdaptiveCodec
from logorrhythm.api import decode, encode, ensure_response_correlation
from logorrhythm.capabilities import Capability, negotiate, supports
from logorrhythm.encoding import (
    ReplayNonceStore,
    SecurityConfig,
    decode_agent_payload_v2,
    decode_message,
    encode_agent_payload_v2,
    encode_message,
)
from logorrhythm.exceptions import DecodingError, EncodingError
from logorrhythm.handshake import perform_handshake
from logorrhythm.observer import emit_event
from logorrhythm.registry import AgentRegistry
from logorrhythm.spec import MessageType, PROTOCOL_VERSION
from logorrhythm.streaming import encode_stream, iter_stream_text


class ConformanceSuiteTests(unittest.TestCase):
    def test_encode_decode_roundtrip_string_ids(self):
        encoded = encode(task="hello", src="agent.alpha", dst="agent.beta")
        self.assertEqual(decode(encoded), "hello")

    def test_long_id_stress(self):
        long_id = "a" * 255
        payload = encode_agent_payload_v2(source_id=long_id, destination_id="b", instruction="HANDOFF", task="t")
        decoded = decode_agent_payload_v2(payload, nonce_store=ReplayNonceStore())
        self.assertEqual(decoded.source_id, long_id)

    def test_invalid_id_rejection(self):
        with self.assertRaisesRegex(EncodingError, "malformed ID"):
            encode_agent_payload_v2(source_id="bad id", destination_id="agent-b", instruction="HANDOFF", task="x")

    def test_correlation_enforcement_match_and_mismatch(self):
        payload = encode_agent_payload_v2(source_id="a", destination_id="b", instruction="HANDOFF", task="x")
        decoded = decode_agent_payload_v2(payload, nonce_store=ReplayNonceStore())
        ensure_response_correlation(decoded.correlation_id, decoded.correlation_id)
        with self.assertRaisesRegex(DecodingError, "mismatched correlation_id"):
            ensure_response_correlation(decoded.correlation_id, "4dbf1d5e-57df-4514-8e20-963fd4f065ca")

    def test_secure_envelope_valid_signature(self):
        secret = b"shared-secret"
        payload = encode_agent_payload_v2(
            source_id="a",
            destination_id="b",
            instruction="HANDOFF",
            task="x",
            nonce=1,
            shared_secret=secret,
            secure_mode=True,
        )
        msg = encode_message(message_type=MessageType.AGENT, payload=payload, version=PROTOCOL_VERSION, flags=0b10, transport_base64=True)
        decoded = decode_message(msg, security=SecurityConfig(shared_secret=secret, secure_mode=True), nonce_store=ReplayNonceStore())
        self.assertEqual(decoded.version, PROTOCOL_VERSION)

    def test_secure_envelope_invalid_signature(self):
        secret = b"shared-secret"
        payload = encode_agent_payload_v2(
            source_id="a",
            destination_id="b",
            instruction="HANDOFF",
            task="x",
            nonce=2,
            shared_secret=secret,
            secure_mode=True,
        )
        tampered = payload[:-1] + (b"0" if payload[-1:] != b"0" else b"1")
        msg = encode_message(message_type=MessageType.AGENT, payload=tampered, version=PROTOCOL_VERSION, flags=0b10, transport_base64=True)
        with self.assertRaisesRegex(DecodingError, "invalid signature"):
            decode_message(msg, security=SecurityConfig(shared_secret=secret, secure_mode=True), nonce_store=ReplayNonceStore())

    def test_replay_protection(self):
        payload = encode_agent_payload_v2(
            source_id="a",
            destination_id="b",
            instruction="HANDOFF",
            task="x",
            nonce=42,
            shared_secret=b"secret",
            secure_mode=True,
        )
        store = ReplayNonceStore()
        security = SecurityConfig(shared_secret=b"secret", secure_mode=True)
        decode_agent_payload_v2(payload, security=security, nonce_store=store)
        with self.assertRaisesRegex(DecodingError, "replayed nonce"):
            decode_agent_payload_v2(payload, security=security, nonce_store=store)

    def test_replay_check_only_when_secure_mode_enabled(self):
        payload = encode_agent_payload_v2(source_id="a", destination_id="b", instruction="HANDOFF", task="x", nonce=42)
        decode_agent_payload_v2(payload)
        decode_agent_payload_v2(payload)

    def test_missing_signature_rejected_when_secure(self):
        payload = encode_agent_payload_v2(source_id="a", destination_id="b", instruction="HANDOFF", task="x", nonce=5)
        msg = encode_message(message_type=MessageType.AGENT, payload=payload, version=PROTOCOL_VERSION, transport_base64=True)
        with self.assertRaisesRegex(DecodingError, "missing signature"):
            decode_message(msg, security=SecurityConfig(shared_secret=b"secret", secure_mode=True), nonce_store=ReplayNonceStore())

    def test_streaming_frame_reassembly(self):
        frames = encode_stream("abcdef", chunk_size=2)
        self.assertEqual("".join(iter_stream_text(frames)), "abcdef")

    def test_adaptive_aliasing_stability(self):
        codec = AdaptiveCodec(warmup_hits=2)
        first = codec.encode("HANDOFF")
        second = codec.encode("HANDOFF")
        third = codec.encode("HANDOFF")
        self.assertEqual(first[0], 0xA1)
        self.assertEqual(second[0], 0xA0)
        self.assertEqual(third, second)

    def test_handshake_registry_and_heartbeat_and_stale_removal(self):
        registry = AgentRegistry()
        state = perform_handshake(
            registry=registry,
            local_id="local",
            peer_id="peer",
            local_capabilities=int(Capability.STREAMING | Capability.HEARTBEAT),
            peer_capabilities=int(Capability.HEARTBEAT),
            last_seen=100.0,
        )
        self.assertEqual(state.peer_id, "peer")
        self.assertIsNotNone(registry.get_agent("peer"))
        registry.update_heartbeat("peer", last_seen=150.0)
        self.assertEqual(registry.get_agent("peer").last_seen, 150.0)
        removed = registry.remove_stale_agents(timeout=10.0, now=200.0)
        self.assertEqual(removed, ["peer"])

    def test_capability_mismatch_fallback(self):
        local = int(Capability.STREAMING | Capability.SECURE_ENVELOPE)
        peer = int(Capability.HEARTBEAT)
        common = negotiate(local, peer)
        self.assertEqual(common, 0)
        self.assertFalse(supports(common, Capability.SECURE_ENVELOPE))

    def test_malformed_packet_rejection(self):
        with self.assertRaisesRegex(DecodingError, "Message too short for header"):
            decode_message("AQ")

    def test_invalid_signature_bytes_raise_decoding_error(self):
        secret = b"shared-secret"
        payload = bytearray(
            encode_agent_payload_v2(
                source_id="a",
                destination_id="b",
                instruction="HANDOFF",
                task="x",
                nonce=3,
                shared_secret=secret,
                secure_mode=True,
            )
        )
        payload[-1] = 0xFF
        msg = encode_message(message_type=MessageType.AGENT, payload=bytes(payload), version=PROTOCOL_VERSION, flags=0b10)
        with self.assertRaisesRegex(DecodingError, "invalid length for signature"):
            decode_message(msg, security=SecurityConfig(shared_secret=secret, secure_mode=True), nonce_store=ReplayNonceStore())

    def test_uuid4_version_enforced_for_correlation(self):
        with self.assertRaisesRegex(DecodingError, "correlation_id must be UUID4"):
            ensure_response_correlation("6ba7b810-9dad-11d1-80b4-00c04fd430c8", "6ba7b810-9dad-11d1-80b4-00c04fd430c8")

    def test_inspect_renders_human_readable(self):
        import io
        from contextlib import redirect_stdout

        from logorrhythm.cli import main

        encoded = encode(task="inspect-me", src="agent.a", dst="agent.b")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["inspect", encoded])
        self.assertEqual(rc, 0)
        self.assertIn("inspect-me", buf.getvalue())


    def test_token_benchmark_cli_table(self):
        import io
        from contextlib import redirect_stdout

        from logorrhythm.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["token-benchmark"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("Token benchmark report", out)
        self.assertIn("single_control", out)
        self.assertIn("nested_payload", out)

    def test_structured_log_required_fields(self):
        event = emit_event(
            correlation_id="cid",
            source_id="a",
            destination_id="b",
            instruction="HANDOFF",
            payload_size_bytes=10,
            total_size_bytes=20,
            latency_ms=1.5,
            status="success",
            signature_verified=True,
        )
        payload = json.loads(event.to_json_line())
        for key in (
            "timestamp",
            "correlation_id",
            "source_id",
            "destination_id",
            "instruction",
            "payload_size_bytes",
            "total_size_bytes",
            "latency_ms",
            "status",
            "signature_verified",
        ):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
