import unittest
from pathlib import Path

from logorrhythm.addressing import AddressBook, AgentAddress
from logorrhythm.benchmark_sync import compute_rows, sync_readme_benchmark_table
from logorrhythm.chunking import chunk_payload, reassemble_chunks
from logorrhythm.cross_model import run_cross_model_benchmark
from logorrhythm.heartbeat import DeadAgentDetector, HeartbeatConfig
from logorrhythm.layer2 import V003_OPS, estimate_token_delta


class ChunkingTests(unittest.TestCase):
    def test_chunk_round_trip(self):
        payload = b"abc" * 1000
        frames = chunk_payload(payload, chunk_size=128)
        self.assertGreater(len(frames), 1)
        reconstructed = reassemble_chunks(list(reversed(frames)))
        self.assertEqual(reconstructed, payload)


class AddressingTests(unittest.TestCase):
    def test_address_encode_decode_and_book(self):
        addr = AgentAddress(region="us-east-1", node="n7", model="gpt-5", shard=3, agent=1092)
        encoded = addr.encode()
        decoded = AgentAddress.decode(encoded)
        self.assertEqual(decoded, addr)

        book = AddressBook()
        identifier = book.register(addr)
        self.assertEqual(book.resolve(identifier), addr)


class HeartbeatTests(unittest.TestCase):
    def test_dead_agent_requires_multiple_misses(self):
        detector = DeadAgentDetector(HeartbeatConfig(interval_s=1.0, grace_misses=2))
        detector.heartbeat("a1", now=0.0)
        self.assertFalse(detector.is_suspected_dead("a1", now=2.5))
        self.assertTrue(detector.is_suspected_dead("a1", now=3.1))


class Layer2Tests(unittest.TestCase):
    def test_expanded_ops_and_delta(self):
        self.assertIn("Q", V003_OPS)
        self.assertIn("P", V003_OPS)
        delta = estimate_token_delta(
            python_program="if conf > 0.8: run_parallel(tasks)",
            layer2_program="Q conf>0.8 P tasks J",
        )
        self.assertGreater(delta.reduction_percent, 0.0)


class BenchmarkSyncTests(unittest.TestCase):
    def test_rows_include_current_release(self):
        rows = compute_rows()
        transports = [r.transport for r in rows]
        self.assertEqual(transports, [
            "JSON baseline",
            "Logorrhythm base64",
            "Logorrhythm binary",
            "Logorrhythm adaptive repeated exchange",
        ])

    def test_sync_updates_readme_marked_section(self):
        table = sync_readme_benchmark_table()
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn(table, readme)


class CrossModelHarnessTests(unittest.TestCase):
    def test_harness_collects_token_counts(self):
        def sender(payload: str):
            return payload + "-relay", 12, 5

        def receiver(payload: str):
            return payload, 8, 3

        result = run_cross_model_benchmark(
            encoded_payload="abc",
            sender_model="model-a",
            receiver_model="model-b",
            sender_call=sender,
            receiver_call=receiver,
        )
        self.assertEqual(result.total_tokens, 28)


if __name__ == "__main__":
    unittest.main()
