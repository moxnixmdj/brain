from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_structured_binary_direct_adequacy_v1 as codec


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
GOAL = (
    "Encode the JSON value in canonical/astra_runtime/tmp/R2_CODEC_SOURCE.json "
    "as MessagePack and save it to canonical/astra_runtime/tmp/R2_CODEC_OUTPUT.msgpack."
)


class R2StructuredBinaryDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.src = TMP / "R2_CODEC_SOURCE.json"
        self.out = TMP / "R2_CODEC_OUTPUT.msgpack"
        self.src.write_text(json.dumps([{"id": 1, "text": "alpha"}]), encoding="utf-8")
        if self.out.exists():
            self.out.unlink()

    def tearDown(self):
        for p in (self.src, self.out):
            if p.exists():
                p.unlink()

    def test_real_registry_preflight_finds_verified_goal_scoped_codec_policy(self):
        out = codec.preflight({"task_id": "codec-preflight", "goal": GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_CODEC_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["format"], "msgpack")
        self.assertTrue(out["policy_id"].startswith("BOUND_CAPABILITY_POLICY::"))
        self.assertEqual(out["json_path"], str(self.src.relative_to(ROOT)).replace("\\", "/"))
        self.assertEqual(out["output_path"], str(self.out.relative_to(ROOT)).replace("\\", "/"))
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_is_not_in_exact_cell(self):
        out = codec.preflight({
            "task_id": "codec-extra",
            "goal": GOAL + " Then upload it somewhere.",
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    @patch.object(codec.live_bound, "run_raw_goal")
    def test_independent_semantic_decode_commits_and_proves_adequacy(self, execute):
        pf = codec.preflight({"task_id": "codec-pass", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.out.write_bytes(b"producer-binary")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }
        execute.side_effect = fake_execute

        out = codec.run(
            {"task_id": "codec-pass", "goal": GOAL},
            verifier_provider=lambda _: {
                "verified": True,
                "producer_independent": True,
                "dependency_independent": True,
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertTrue(self.out.is_file())
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    @patch.object(codec.live_bound, "run_raw_goal")
    def test_failed_independent_acceptance_rolls_back_new_artifact(self, execute):
        pf = codec.preflight({"task_id": "codec-fail", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.out.write_bytes(b"bad-binary")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }
        execute.side_effect = fake_execute

        out = codec.run(
            {"task_id": "codec-fail", "goal": GOAL},
            verifier_provider=lambda _: {"verified": False},
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(self.out.exists())
        self.assertFalse(out["policy_adequacy_authority"])

    @patch.object(codec.live_bound, "run_raw_goal")
    def test_failed_acceptance_restores_preexisting_artifact_bytes(self, execute):
        old = b"old-good-bytes"
        self.out.write_bytes(old)
        pf = codec.preflight({"task_id": "codec-restore", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            self.out.write_bytes(b"replacement-bad")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }
        execute.side_effect = fake_execute

        out = codec.run(
            {"task_id": "codec-restore", "goal": GOAL},
            verifier_provider=lambda _: {
                "verified": True,
                "producer_independent": False,
            },
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(self.out.read_bytes(), old)


if __name__ == "__main__":
    unittest.main(verbosity=2)
