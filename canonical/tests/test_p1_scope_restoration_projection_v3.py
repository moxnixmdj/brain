from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "projection": "canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V1.json",
    "closure": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "restoration": "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V3.json",
    "restoration_verification": "canonical/verification/P1_COMPOSITE_PROOF_RESTORATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json",
    "synthesis_exhaustion": "canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json",
}


def load(key):
    return json.loads((ROOT / PATHS[key]).read_text(encoding="utf-8"))


def git_blob_sha(rel):
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class P1ScopeRestorationProjectionV3Tests(unittest.TestCase):
    def test_restoration_authority_is_independently_verified(self):
        restoration = load("restoration")
        verification = load("restoration_verification")
        self.assertTrue(restoration["status"].startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"), restoration)
        self.assertTrue(verification["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"), verification)
        self.assertIn("WHOLE_FROZEN_P1_CONTRACT_PASS", restoration["restored"])
        self.assertIn("POSTWAVE_12_OF_12_WHOLE_CONTRACT_CLAIM", restoration["restored"])
        self.assertIn("P1_WITNESS_TRANSPORT_INTO_RECOVERY_ACCEPTANCE", restoration["explicitly_not_restored"])
        self.assertEqual(restoration["opus55_predicate_credit_delta"], 0)
        self.assertEqual(restoration["family_credit_delta"], 0)

    def test_all_four_projections_agree(self):
        authority = load("authority")
        projection = load("projection")
        closure = load("closure")
        matrix = load("matrix")

        self.assertEqual(authority["truth"]["contracts"], "12/12_WHOLE_SCOPE_PASS__P1_COMPOSITE_SCOPE_RESTORED__RAW_TERMINAL_EVIDENCE_PRESERVED")
        self.assertEqual(authority["truth"]["behavioral_families"], "19/19_PROVISIONAL_BEHAVIORAL_PASS__8_P1_DEPENDENT_ROWS_RESTORED")
        self.assertEqual(authority["truth"]["opus55_acceptance"], "2/19_PASS__17/19_OPEN")
        self.assertFalse(authority["truth"]["achieved"])

        self.assertEqual(projection["current_truth"]["whole_scope_contracts"], "12/12_PASS__P1_WHOLE_SCOPE_RESTORED")
        self.assertEqual(projection["current_truth"]["behavioral_families"], "19/19_PROVISIONAL_BEHAVIORAL_PASS__8_P1_DEPENDENT_ROWS_RESTORED")
        self.assertEqual(projection["current_truth"]["opus55_acceptance"], "2/19_CLOSED__17/19_OPEN")
        self.assertEqual(projection["current_truth"]["verified_owned"], "2/19")
        self.assertEqual(projection["current_truth"]["atomic_acceptance_frontier"], "7/38_PROVED__31_UNRESOLVED")
        self.assertFalse(projection["current_truth"]["terminal_goal_achieved"])

        self.assertEqual(closure["behavioral_pass_family_count"], 19)
        self.assertEqual(closure["behavioral_quarantined_family_count"], 0)
        self.assertEqual(closure["verified_closed_family_count"], 2)
        self.assertEqual(closure["open_family_count"], 17)
        self.assertEqual(closure["counters"]["unproved_required_behaviors"], 0)
        self.assertFalse(closure["current_machine_verdict"]["achieved"])
        self.assertEqual(closure["opus55_acceptance_summary"]["calibrated_family_count"], 2)
        self.assertEqual(closure["opus55_acceptance_summary"]["pending_family_count"], 17)
        self.assertEqual(closure["opus55_acceptance_summary"]["atomic_predicates"], {
            "proved": 7, "unresolved": 31, "total": 38
        })

        restored = [
            row for row in matrix["rows"]
            if row.get("current_behavioral_scope_state") ==
            "P1_WHOLE_SCOPE_RESTORED__PROVISIONAL_BEHAVIORAL_FAMILY_PASS_REINSTATED"
        ]
        quarantined = [
            row for row in matrix["rows"]
            if "P1_WHOLE_SCOPE_QUARANTINED" in str(row.get("current_behavioral_scope_state", ""))
        ]
        self.assertEqual(len(restored), 8, restored)
        self.assertEqual(quarantined, [])
        self.assertEqual(matrix["p1_scope_restoration"]["restored_family_count"], 8)
        self.assertEqual(matrix["p1_scope_restoration"]["opus55_acceptance_unchanged"], "2_OF_19_CLOSED__17_OPEN")

    def test_authority_content_addressed_pointers_match_current_blobs(self):
        authority = load("authority")
        expected = {
            "terminal_closure_manifest": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
            "ownership_matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
            "terminal_projection_consistency": "canonical/governance/TERMINAL_PROJECTION_CONSISTENCY_V1.json",
            "p1_composite_restoration_activation": "canonical/governance/P1_COMPOSITE_PROOF_RESTORATION_ACTIVATION_V3.json",
            "p1_composite_restoration_verification": "canonical/verification/P1_COMPOSITE_PROOF_RESTORATION_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json",
            "synthesis_zero_reality_exhaustion": "canonical/governance/OPUS55_SYNTHESIS_ZERO_REALITY_DISCHARGE_EXHAUSTION_V1.json",
        }
        for key, rel in expected.items():
            source = authority["sources"][key]
            self.assertEqual(source["path"], rel, key)
            self.assertEqual(source["git_blob_sha"], git_blob_sha(rel), key)

    def test_synthesis_exhausted_action_is_not_scheduled(self):
        authority = load("authority")
        exhaustion = load("synthesis_exhaustion")
        self.assertFalse(exhaustion["current_zero_reality_discharge_available"])
        frontier = authority["compiled_next_frontier"]
        self.assertNotEqual(frontier["primary_action_id"], "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
        self.assertNotIn("DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA", frontier["available_zero_reality_critical_actions"])
        self.assertNotEqual(frontier["primary_action_id"], "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
        self.assertEqual(frontier["stale_action_revocation"]["authority_git_blob_sha"], git_blob_sha(PATHS["synthesis_exhaustion"]))

    def test_tb4_and_acceptance_firewalls_remain_closed(self):
        authority = load("authority")
        tb4 = authority["tb4_threshold_execution"]
        self.assertEqual(tb4["maximum_attainable_successes"], 180)
        self.assertEqual(tb4["required_successes"], 220)
        self.assertFalse(tb4["execution_authorized"])
        atomic = authority["atomic_acceptance_frontier"]
        self.assertEqual((atomic["proved"], atomic["unresolved"], atomic["total"]), (7, 31, 38))
        self.assertEqual(atomic["authorized_acceptance_case_actions"], [])
        self.assertFalse(authority["truth"]["achieved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
