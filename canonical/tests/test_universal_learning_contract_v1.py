from __future__ import annotations

import unittest

from canonical.runtime import universal_learning_contract_v1 as ulc


class UniversalLearningContractV1Tests(unittest.TestCase):
    def test_only_literal_true_can_use_known_capability(self):
        self.assertEqual(
            ulc.route_input(verified_coverage=True)["route"],
            "USE_VERIFIED_CAPABILITY",
        )
        for value in (False, None, 0, 1, "", "true", [], {}):
            out = ulc.route_input(verified_coverage=value)
            self.assertEqual(out["route"], "LEARN", value)
            self.assertTrue(out["unknown_captured"], value)
            self.assertFalse(out["trusted_execution_authorized"], value)

    def test_learning_uses_transfer_and_active_information_channels(self):
        out = ulc.learning_request(
            missing_question="learn unseen language",
            prior_knowledge_refs=["programming-semantics", "compiler-knowledge"],
        )
        self.assertEqual(out["state"], "LEARNING")
        self.assertIn("TRANSFER_PRIOR_KNOWLEDGE", out["channels"])
        self.assertIn("RETRIEVE_DIRECT_OR_INDIRECT_EVIDENCE", out["channels"])
        self.assertIn("OBSERVE_ENVIRONMENT", out["channels"])
        self.assertIn("SAFE_EXPERIMENT", out["channels"])
        self.assertIn("DERIVE_AND_REASON", out["channels"])
        self.assertFalse(out["candidate_trusted"])
        self.assertFalse(out["promotion_authorized"])

    def test_unknown_learning_channel_fails_closed(self):
        with self.assertRaises(ulc.UniversalLearningContractError):
            ulc.learning_request(
                missing_question="x",
                channels=["MAGIC_ORACLE"],
            )

    def test_candidate_cannot_promote_before_verification(self):
        self.assertFalse(ulc.promotion_allowed("UNKNOWN"))
        self.assertFalse(ulc.promotion_allowed("LEARNING"))
        self.assertFalse(ulc.promotion_allowed("CANDIDATE"))
        self.assertFalse(ulc.promotion_allowed("REJECTED"))
        self.assertTrue(ulc.promotion_allowed("VERIFIED"))

    def test_failed_verification_is_rejected(self):
        out = ulc.verify_candidate(candidate_id="candidate-1", verification_pass=False)
        self.assertEqual(out["state"], "REJECTED")
        self.assertFalse(out["trusted"])
        self.assertFalse(out["promotion_authorized"])

    def test_passed_verification_is_reusable(self):
        out = ulc.verify_candidate(candidate_id="candidate-1", verification_pass=True)
        self.assertEqual(out["state"], "VERIFIED")
        self.assertTrue(out["trusted"])
        self.assertTrue(out["promotion_authorized"])
        self.assertEqual(
            ulc.transition("VERIFIED", "REUSE"),
            "VERIFIED",
        )

    def test_environment_change_invalidates_prior_trust(self):
        self.assertEqual(
            ulc.transition("VERIFIED", "ENVIRONMENT_CHANGED"),
            "UNKNOWN",
        )

    def test_forbidden_shortcuts_fail_closed(self):
        forbidden = [
            ("UNKNOWN", "VERIFY_PASS"),
            ("UNKNOWN", "REUSE"),
            ("LEARNING", "VERIFY_PASS"),
            ("CANDIDATE", "REUSE"),
            ("REJECTED", "REUSE"),
        ]
        for state, event in forbidden:
            with self.subTest(state=state, event=event):
                with self.assertRaises(ulc.UniversalLearningContractError):
                    ulc.transition(state, event)

    def test_complete_control_theorem_passes_without_semantic_overclaim(self):
        out = ulc.prove_control_invariants()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["finite_control_pairs_checked"],
            len(ulc.STATES) * len(ulc.EVENTS),
        )
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["tool_learning_noninferiority_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
