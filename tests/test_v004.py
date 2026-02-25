import unittest

from logorrhythm import decode, encode, receive, send
from logorrhythm.adaptive import AdaptiveCodec, benchmark_adaptive_vs_static
from logorrhythm.fault_tolerance import Checkpoint, CheckpointStore
from logorrhythm.identity import issue_challenge, prove_identity, verify_identity
from logorrhythm.streaming import encode_stream, iter_stream_text
from logorrhythm.topology import broadcast, mesh, multicast, pipeline
from logorrhythm.v004 import compute_v004_metrics


class PublicApiTests(unittest.TestCase):
    def test_minimal_encode_decode_send_receive(self):
        encoded = encode(task="hello")
        self.assertEqual(decode(encoded), "hello")
        self.assertEqual(receive(send(task="world")), "world")


class AdaptiveTests(unittest.TestCase):
    def test_adaptive_improves_static(self):
        result = benchmark_adaptive_vs_static(count=1000)
        self.assertGreater(result.improvement_percent, 0)

    def test_adaptive_round_trip(self):
        codec = AdaptiveCodec(warmup_hits=1)
        payload = codec.encode("HANDOFF")
        self.assertEqual(codec.decode(payload), "HANDOFF")


class StreamingTopologyFaultTests(unittest.TestCase):
    def test_streaming_chunks_reassemble_text(self):
        frames = encode_stream("abcdefghij", chunk_size=3)
        self.assertEqual("".join(iter_stream_text(frames)), "abcdefghij")

    def test_topology_helpers(self):
        self.assertEqual(len(broadcast("a", ["b", "c"], "x")), 2)
        self.assertEqual(len(multicast("a", ["g1"], "x")), 1)
        self.assertIn("s2", pipeline(["s1", "s2"], "x"))
        self.assertEqual(len(mesh("a", ["b", "c"], "x")), 2)

    def test_checkpoint_reassign(self):
        store = CheckpointStore()
        data = store.snapshot(Checkpoint(task_id="t1", owner="a1", step=4, state="half"))
        store.restore(data)
        cp = store.reassign("t1", "a9")
        self.assertEqual(cp.owner, "a9")


class IdentityTests(unittest.TestCase):
    def test_handshake(self):
        challenge = issue_challenge()
        proof = prove_identity(agent_id="a1", challenge=challenge, shared_secret="s3")
        self.assertTrue(verify_identity(agent_id="a1", challenge=challenge, shared_secret="s3", proof=proof))


class BenchmarkOutputTests(unittest.TestCase):
    def test_v004_numbers_beat_v003(self):
        metrics = compute_v004_metrics()
        self.assertGreater(metrics["byte_reduction"], 24.37)
        self.assertGreater(metrics["throughput_gain"], 38.87)
        self.assertGreater(metrics["latency_improvement"], 25.64)



if __name__ == "__main__":
    unittest.main()
