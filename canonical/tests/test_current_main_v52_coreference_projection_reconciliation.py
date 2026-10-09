from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ONE = ROOT / "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"
ACT = ROOT / "canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V27.json"
VERIFY = ROOT / "canonical/verification/R2_FINANCE_COREFERENCE_AMBIGUITY_CONTROL_VERIFY_20261009_V2.json"
REC = ROOT / "canonical/governance/CURRENT_MAIN_V52_COREFERENCE_PROJECTION_RECONCILIATION_20261009_V1.json"

EXPECTED = {
    R2: "41f003364db7602184146ceb84706771e0c69c78",
    TERM: "220864c89077a8cd08b05f5f3f729536ead8bd0e",
    ONE: "a4f10f8aee8ee61189dcc3eeacbbdfa254915dc3",
    ACT: "e400484c325c96aa56c7a9635db3a01ace46fdbb",
    VERIFY: "dec5f52893f4e26b8135408f7969390020fc861b",
    REC: "72d20881e562ab2295a5b1fa5a6aac0742fccfe6",
}


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class CurrentMainV52CoreferenceProjectionReconciliationTests(unittest.TestCase):
    def test_exact_subject_bytes_match(self):
        for path, expected in EXPECTED.items():
            self.assertEqual(blob(path), expected, str(path))

    def test_r2_pointer_projects_v52_without_global_coreference_overclaim(self):
        r2 = load(R2)
        self.assertIn("__V52__", r2["status"])
        self.assertEqual(r2["direct_adequacy"]["current_route_count"], 34)
        self.assertEqual(r2["direct_adequacy"]["bounded_family_count"], 31)
        self.assertEqual(
            r2["direct_adequacy"]["direct_runtime_path"],
            "canonical/runtime/r2_direct_end_to_end_adequacy_v15.py",
        )
        self.assertEqual(
            r2["direct_adequacy"]["activation_git_blob_sha"],
            blob(ACT),
        )
        self.assertEqual(
            r2["direct_adequacy"]["latest_verification_git_blob_sha"],
            blob(VERIFY),
        )
        p = r2["fixed_point_information_policy"]
        self.assertTrue(p["bounded_finance_coreference_ambiguity_control"])
        self.assertTrue(
            p["terminally_equivalent_coreference_candidates_need_no_identity_resolution"]
        )
        self.assertTrue(
            p["terminally_distinct_coreference_candidates_use_minimum_declared_discriminator"]
        )
        self.assertTrue(p["unproved_mention_universe_completeness_remains_open"])
        self.assertTrue(p["antecedent_identity_not_self_certified"])
        self.assertIn("GENERAL_IMPLICIT_OR_OPEN_WORLD_COREFERENCE", r2["remaining_hard_frontier"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL", r2["status"])

    def test_terminal_and_one_shot_cross_pointer_invariants_match_v52(self):
        terminal = load(TERM)
        one = load(ONE)
        self.assertEqual(terminal["pointer_revision"], 83)
        self.assertEqual(
            terminal["live_truth"]["current_r2_pointer_git_blob_sha"],
            blob(R2),
        )
        self.assertEqual(terminal["live_truth"]["r2_direct_adequacy_route_count"], 34)
        self.assertEqual(
            terminal["live_truth"]["r2_direct_adequacy_bounded_family_count"], 31
        )
        self.assertTrue(
            terminal["live_truth"]["r2_bounded_coreference_ambiguity_control_bound"]
        )
        self.assertFalse(terminal["live_truth"]["r2_general_coreference_closed"])
        self.assertFalse(
            terminal["live_truth"]["r2_open_world_mention_completeness_proved"]
        )
        self.assertEqual(terminal["live_truth"]["r2_primary_internal_unsolved_count"], 1)
        self.assertFalse(terminal["live_truth"]["terminal"])

        auth = one["authority"]
        self.assertEqual(auth["current_r2_pointer_git_blob_sha"], blob(R2))
        self.assertEqual(auth["current_terminal_authority_git_blob_sha"], blob(TERM))
        self.assertEqual(auth["current_terminal_authority_pointer_revision"], 83)
        self.assertEqual(auth["current_r2_direct_route_count"], 34)
        self.assertEqual(auth["current_r2_bounded_family_count"], 31)
        self.assertTrue(auth["r2_bounded_coreference_ambiguity_control_bound"])
        self.assertFalse(auth["r2_general_coreference_closed"])
        self.assertFalse(auth["terminal_authority"])
        self.assertFalse(
            one["current_main_v52_coreference_projection_reconciliation"]["terminal"]
        )

    def test_activation_is_delta_only_and_preserves_authority_boundary(self):
        activation = load(ACT)
        delta = activation["delta"]
        self.assertEqual(activation["counts"]["current_route_count"], 34)
        self.assertEqual(activation["counts"]["bounded_family_count"], 31)
        self.assertEqual(
            delta["route_id"],
            "DIRECT_ADEQUACY::FINANCE_BOUNDED_COREFERENCE_AMBIGUITY_CONTROL_V1",
        )
        self.assertEqual(delta["verification"]["git_blob_sha"], blob(VERIFY))
        boundary = activation["authority_boundary"]
        self.assertFalse(boundary["antecedent_identity_asserted"])
        self.assertFalse(boundary["general_coreference_resolution_claimed"])
        self.assertFalse(boundary["open_world_mention_completeness_claimed"])
        self.assertFalse(boundary["terminal_authority"])
        self.assertEqual(boundary["terminal_credit_delta"], 0)

    def test_reconciliation_keeps_only_the_real_remaining_finance_frontier(self):
        rec = load(REC)
        truth = rec["current_truth"]
        self.assertEqual(truth["r2_primary_internal_unsolved_count"], 1)
        self.assertEqual(truth["r2_primary_internal_cell"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertEqual(truth["r2_direct_route_count"], 34)
        self.assertEqual(truth["r2_bounded_family_count"], 31)
        self.assertTrue(truth["bounded_coreference_control_owned"])
        self.assertFalse(truth["general_coreference_closed"])
        self.assertFalse(truth["terminal"])
        self.assertEqual(rec["accounting"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
