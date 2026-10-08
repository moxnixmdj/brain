from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class R2AdvisoryJudgmentPolicyV1Tests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (
                ROOT
                / "canonical/governance/R2_BRAIN_OWNED_ADVISORY_JUDGMENT_POLICY_20261008_V1.json"
            ).read_text(encoding="utf-8")
        )
        self.current = json.loads(
            (
                ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
            ).read_text(encoding="utf-8")
        )

    def test_closed_external_model_is_not_load_bearing(self):
        closed = self.policy["closed_external_model_policy"]
        self.assertFalse(closed["runtime_dependency_allowed"])
        self.assertFalse(closed["semantic_authority_allowed"])
        self.assertFalse(closed["acceptance_authority_allowed"])
        self.assertFalse(closed["capability_ownership_credit_allowed"])
        self.assertTrue(closed["reference_or_interface_inspiration_allowed"])

    def test_brain_owned_scorer_is_advisory_only(self):
        kernel = self.policy["brain_owned_judgment_kernel_policy"]
        self.assertIn("CANDIDATE_POLICY_RANKING", kernel["allowed_roles"])
        self.assertIn("SELF_CERTIFY_POLICY_ADEQUACY", kernel["forbidden_roles"])
        self.assertIn("SELF_CERTIFY_GOAL_SATISFACTION", kernel["forbidden_roles"])
        self.assertIn(
            "EXPLICIT_ABSTAIN_OR_NO_ADEQUATE_CANDIDATE_OUTPUT",
            kernel["minimum_admission_requirements"],
        )

    def test_open_world_none_or_abstain_is_preserved(self):
        self.assertIn(
            "NO_FIXED_LABEL_OR_CANDIDATE_SET_IS_ASSUMED_COMPLETE",
            self.policy["open_world_rule"],
        )
        self.assertIn("NONE_OR_ABSTAIN", self.policy["open_world_rule"])

    def test_current_pointer_keeps_policy_cover_as_authority(self):
        self.assertFalse(self.current["external_closed_model_dependency"])
        self.assertEqual(
            self.current["learned_judgment_role"],
            "ADVISORY_GENERATION_RANKING_AND_SEARCH_ACCELERATION_ONLY",
        )
        self.assertEqual(
            self.current["authority"],
            "AUTHENTICATED_POLICY_COVER_MINIMUM_POLICY_CHANGING_INFORMATION_AND_INDEPENDENT_GOAL_ACCEPTANCE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
