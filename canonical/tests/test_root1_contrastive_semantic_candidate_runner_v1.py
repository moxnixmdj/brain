import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import root1_contrastive_semantic_candidate_runner_v1 as runner


class Root1ContrastiveSemanticCandidateRunnerTests(unittest.TestCase):
    def test_exact_subject_hash_and_size_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.gguf"
            raw = b"abc123" * 100
            path.write_bytes(raw)
            out = runner.verify_subject(
                path,
                expected_sha256=hashlib.sha256(raw).hexdigest(),
                expected_bytes=len(raw),
            )
            self.assertEqual(out["bytes"], len(raw))

    def test_nonlocal_endpoint_rejected(self):
        with self.assertRaisesRegex(runner.CandidateRunnerError, "LOCALHOST"):
            runner._local_endpoint("https://example.com/v1/chat/completions")

    def test_full_candidate_run_binds_subject_and_gate(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.gguf"
            raw = b"model"
            path.write_bytes(raw)
            good = {
                "PARA_A": "Before sunrise Tuesday, Neris brought seven amber parcels to Corin.",
                "PARA_B": "After sunset Wednesday, Neris brought nine blue parcels to Corin.",
                "SIMPLE_A": "Yusuf shut Pump 3 as the eastern valve hit 82 degrees, before moving 45 liters to Tank B.",
                "SIMPLE_B": "Yusuf opened Pump 3 after the western valve fell below 18 degrees, moving 15 liters from Tank B.",
                "SUM_A": "Train 8, delayed 35 minutes outside Luxor, had two signal boxes inspected with no damage and reached Aswan at 21:10.",
                "SUM_B": "Train 8 stopped 50 minutes near Edfu, where three signal boxes showed damage, then returned to Luxor at 22:40.",
                "STORY_A": "ORION-7 found BRASS-KEY at GATE-2. It crossed HARBOR-9 carrying the key safely. ORION-7 returned BRASS-KEY to MIRA-1.",
                "STORY_B": "ORION-7 found SILVER-RING at GATE-2. It crossed TUNNEL-4 while protecting the ring. ORION-7 gave SILVER-RING to MIRA-1.",
            }
            sequence = [
                good[probe.probe_id] for probe in runner.gate.frozen_probes()
            ]
            with patch.object(runner, "chat", side_effect=sequence):
                out = runner.run_candidate(
                    model_path=path,
                    expected_sha256=hashlib.sha256(raw).hexdigest(),
                    expected_bytes=len(raw),
                    model_alias="local",
                )
            self.assertEqual(out["status"], "PASS")
            self.assertEqual(out["gate_verdict"]["case_pass_count"], 8)
            self.assertEqual(out["terminal_case_exposure"], 0)
            self.assertEqual(out["acceptance_credit"], 0)


if __name__ == "__main__":
    unittest.main()
