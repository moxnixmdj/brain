from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

ASSURANCE = ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
SCHEDULER = ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
BATCH_VERIFY = ROOT / "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class ProfessionalScopeNestedProjectionConsistencyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assurance = load(ASSURANCE)
        cls.scheduler = load(SCHEDULER)
        cls.mission = load(MISSION)
        cls.batch = load(BATCH_VERIFY)

    def test_independent_batch_receipt_is_exact_24_scope_zero_property(self):
        self.assertEqual(
            git_blob(BATCH_VERIFY),
            "4c2d40a262f18f34bb35f94b59660d60972d45ef",
        )
        replay = self.batch["independent_replay"]
        self.assertEqual(replay["leaf_count"], 24)
        self.assertEqual(replay["domain_equivalence_pass_count"], 24)
        self.assertEqual(replay["scope_complete_count"], 24)
        self.assertEqual(replay["property_truth_count"], 0)
        self.assertFalse(self.batch["quality_authority"])
        self.assertFalse(self.batch["terminal_authority"])

    def test_assurance_nested_projection_matches_batch_truth(self):
        p = self.assurance["professional_whole_leaf_progress"]
        self.assertEqual(p["expected_leaf_count"], 24)
        self.assertEqual(p["admitted_whole_leaf_scope_count"], 24)
        self.assertEqual(p["admitted_scope_count"], 24)
        self.assertEqual(p["property_truth_ready_count"], 24)
        self.assertEqual(p["remaining_scope_construction_count"], 0)
        self.assertEqual(p["property_truth_closed_count"], 0)
        self.assertEqual(p["global_leaf_closed_count"], 0)
        self.assertFalse(p["domain_semantic_closure"])
        self.assertFalse(p["domain_execution_closure"])
        self.assertEqual(
            p["scope_batch_verification_git_blob_sha"],
            "4c2d40a262f18f34bb35f94b59660d60972d45ef",
        )

    def test_scheduler_nested_projection_matches_batch_truth(self):
        p = self.scheduler["whole_leaf_residual_control"]
        self.assertEqual(p["admitted_v2_chain_count"], 24)
        self.assertEqual(p["claim_scope_construction_required_count"], 0)
        self.assertEqual(p["property_truth_ready_count"], 24)
        self.assertEqual(p["property_truth_closed_count"], 0)
        self.assertEqual(
            p["scope_batch_verification_git_blob_sha"],
            "4c2d40a262f18f34bb35f94b59660d60972d45ef",
        )
        self.assertIn("24_SCOPE_COMPLETE", p["status"])
        self.assertIn("0_PROPERTY_TRUTH_CLOSED", p["status"])

    def test_mission_nested_projection_matches_batch_truth(self):
        p = self.mission["professional_whole_leaf_control"]
        self.assertEqual(p["leaf_count"], 24)
        self.assertEqual(p["admitted_v2_chain_count"], 24)
        self.assertEqual(p["claim_scope_construction_required_count"], 0)
        self.assertEqual(p["property_truth_ready_count"], 24)
        self.assertEqual(p["property_truth_closed_count"], 0)
        self.assertEqual(
            p["scope_batch_verification_git_blob_sha"],
            "4c2d40a262f18f34bb35f94b59660d60972d45ef",
        )
        self.assertIn("RUN_PROPERTY_TRUTH_VERIFICATION", p["next"])
        self.assertIn("DO_NOT_REOPEN_SCOPE_CONSTRUCTION", p["next"])

    def test_no_scope_to_property_or_terminal_laundering(self):
        self.assertFalse(self.assurance["terminal_authority"])
        text = "\n".join(
            json.dumps(x, sort_keys=True)
            for x in (self.assurance, self.scheduler, self.mission)
        )
        self.assertNotIn('"property_truth_closed_count": 24', text)
        self.assertNotIn('"global_leaf_closed_count": 24', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
