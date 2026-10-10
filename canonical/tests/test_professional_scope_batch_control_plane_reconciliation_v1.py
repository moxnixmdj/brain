from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "assurance": ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json",
    "reuse": ROOT / "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json",
    "frontier": ROOT / "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json",
    "scheduler": ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json",
    "mission": ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
    "activation": ROOT / "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_ACTIVATION_20261010_V1.json",
    "verification": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
    "r10_slots": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R10_PROOF_SLOT_DIRECT_VERIFY_20261010_V1.json",
}


def load(name: str) -> dict:
    return json.loads(PATHS[name].read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class ProfessionalScopeBatchControlPlaneReconciliationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assurance = load("assurance")
        cls.reuse = load("reuse")
        cls.frontier = load("frontier")
        cls.scheduler = load("scheduler")
        cls.mission = load("mission")
        cls.activation = load("activation")
        cls.verification = load("verification")

    def test_batch_receipt_is_exact_and_scope_only(self):
        self.assertEqual(
            blob(PATHS["verification"]),
            "4c2d40a262f18f34bb35f94b59660d60972d45ef",
        )
        self.assertEqual(
            blob(PATHS["activation"]),
            "d40188f87818d9c6a4507a043380a753ca563e18",
        )
        self.assertTrue(self.verification["status"].startswith("PASS__"))
        replay = self.verification["independent_replay"]
        self.assertEqual(replay["leaf_count"], 24)
        self.assertEqual(replay["domain_equivalence_pass_count"], 24)
        self.assertEqual(replay["scope_complete_count"], 24)
        self.assertEqual(replay["property_truth_count"], 0)
        self.assertFalse(self.verification["quality_authority"])
        self.assertFalse(self.verification["terminal_authority"])
        self.assertEqual(self.verification["terminal_credit_delta"], 0)

    def test_assurance_projection_is_24_scope_0_property(self):
        p = self.assurance["professional_whole_leaf_progress"]
        self.assertEqual(p["expected_leaf_count"], 24)
        self.assertEqual(p["admitted_scope_count"], 24)
        self.assertEqual(p["property_truth_ready_count"], 24)
        self.assertEqual(p["remaining_scope_construction_count"], 0)
        self.assertEqual(p["property_truth_closed_count"], 0)
        self.assertEqual(p["global_leaf_closed_count"], 0)
        self.assertFalse(self.assurance["terminal_authority"])

    def test_reuse_classification_demotes_scope_research(self):
        row = next(
            x for x in self.reuse["classifications"]
            if x["residual_id"] == "PROFESSIONAL_QUALITY_BROAD_EXECUTION"
        )
        batch = row["whole_leaf_scope_batch"]
        self.assertEqual(batch["scope_complete_count"], 24)
        self.assertEqual(batch["property_truth_count"], 0)
        self.assertEqual(batch["scope_construction_remaining"], 0)
        self.assertEqual(
            row["whole_leaf_certificate_gate"]["admitted_scope_chain_count"], 24
        )
        self.assertEqual(
            row["whole_leaf_certificate_gate"]["closed_leaf_property_count"], 0
        )
        self.assertIn(
            "RUN_PROPERTY_TRUTH_VERIFICATION_ON_THE_24_SCOPE_COMPLETE_PROFESSIONAL_CLAIMS_USING_EXISTING_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_MACHINERY",
            self.reuse["next_shared_execution_cut"],
        )

    def test_live_frontier_is_property_truth_not_scope_construction(self):
        self.assertIn("PROPERTY_TRUTH_0_OF_24", self.frontier["status"])
        row = next(
            x for x in self.frontier["candidates"]
            if x["work_id"] == "PROFESSIONAL_QUALITY_V7_WHOLE_LEAF_PROPERTY_TRUTH"
        )
        ev = row["read_only_evidence"]
        self.assertEqual(ev["whole_leaf_scope_certificates_admitted"], 24)
        self.assertEqual(ev["claim_scope_construction_required_count"], 0)
        self.assertEqual(ev["property_truth_ready_count"], 24)
        self.assertEqual(ev["whole_leaf_property_truth_closed"], 0)
        self.assertFalse(ev["property_truth_work_blocked_until_scope_admission"])
        self.assertFalse(self.frontier["live_selection"]["authorized"])

    def test_scheduler_and_mission_bind_reconciled_pointer_bytes(self):
        self.assertEqual(
            self.scheduler["current_live_work_frontier"]["git_blob_sha"],
            blob(PATHS["frontier"]),
        )
        self.assertEqual(
            self.mission["current_parallel_frontier_control"]["observed_git_blob_sha"],
            blob(PATHS["frontier"]),
        )
        self.assertEqual(
            self.mission["current_assurance_closure_compiler"]["observed_git_blob_sha"],
            blob(PATHS["assurance"]),
        )
        self.assertEqual(
            self.mission["current_residual_reuse_classification"]["observed_git_blob_sha"],
            blob(PATHS["reuse"]),
        )
        self.assertEqual(
            self.mission["current_development_scheduler"]["observed_git_blob_sha"],
            blob(PATHS["scheduler"]),
        )
        ctl = self.mission["professional_whole_leaf_control"]
        self.assertEqual(ctl["admitted_v2_chain_count"], 24)
        self.assertEqual(ctl["claim_scope_construction_required_count"], 0)
        self.assertEqual(ctl["property_truth_ready_count"], 24)
        self.assertEqual(ctl["property_truth_closed_count"], 0)

    def test_r10_structural_slot_currentness_is_not_property_truth(self):
        r10 = load("r10_slots")
        self.assertEqual(
            blob(PATHS["r10_slots"]),
            "d7de9a123c02f46e26e182cd45d95e22eee2ee8c",
        )
        self.assertEqual(
            r10["independent_replay"]["direct_adversarial_cases_passed"], 13
        )
        self.assertFalse(
            r10["authority_boundary"]["underlying_fact_truth_authority"]
        )
        self.assertFalse(
            r10["authority_boundary"]["whole_leaf_property_truth_proved"]
        )
        slots = self.assurance["professional_quality_r10_structural_proof_slots"]
        self.assertEqual(
            slots["verification_git_blob_sha"],
            "d7de9a123c02f46e26e182cd45d95e22eee2ee8c",
        )
        self.assertEqual(slots["direct_adversarial_cases_passed"], 13)
        self.assertFalse(slots["underlying_fact_truth_authority"])
        self.assertFalse(slots["whole_leaf_property_truth_proved"])
        guard = self.assurance["professional_quality_r10_execution_enforcement"]
        self.assertEqual(
            guard["currentness"],
            "HISTORICAL_VERIFICATION_ONLY__VERIFIED_GUARD_RUNTIME_BLOB_DIFFERS_FROM_CURRENT_MAIN_GUARD_RUNTIME",
        )
        self.assertFalse(guard["current_guard_exact_behavioral_reverification_claimed"])
        self.assertFalse(guard["whole_leaf_property_truth_proved"])

    def test_no_scope_to_property_truth_laundering(self):
        texts = "\n".join(
            json.dumps(load(name), sort_keys=True)
            for name in ("assurance", "reuse", "frontier", "scheduler", "mission")
        )
        self.assertNotIn('"property_truth_closed_count": 24', texts)
        self.assertNotIn('"global_leaf_closed_count": 24', texts)
        self.assertIn('"property_truth_closed_count": 0', texts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
