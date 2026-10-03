from __future__ import annotations

import unittest

from canonical.runtime import universal_learning_active_router_v2 as router


class UniversalLearningActiveRouterV2Tests(unittest.TestCase):
    def test_verified_coverage_requires_zero_novelty_delta(self):
        out = router.route(
            goal="reuse known mechanism",
            verified_coverage=True,
            required_facts={"a", "b"},
            verified_facts={"a", "b"},
            hypotheses=[],
            actions=[],
        )
        self.assertEqual(out["route"], "USE_VERIFIED_CAPABILITY")
        self.assertTrue(out["trusted_execution_authorized"])
        self.assertIsNone(out["next_action"])

    def test_claimed_verified_coverage_with_missing_fact_fails_closed_to_learning(self):
        out = router.route(
            goal="handle changed environment",
            verified_coverage=True,
            required_facts={"a", "b"},
            verified_facts={"a"},
            hypotheses=[{"id": "h1", "plausible": True, "best_action": "inspect"}],
            actions=[{"id": "inspect", "decision_gain": 2, "transfer_gain": 1, "proof_gain": 1, "time": 1, "cost": 0, "risk": 0}],
        )
        self.assertEqual(out["route"], "LEARN")
        self.assertEqual(out["reason"], "VERIFIED_COVERAGE_CONTRADICTED_BY_NOVELTY_DELTA")
        self.assertFalse(out["trusted_execution_authorized"])
        self.assertEqual(out["next_action"]["id"], "inspect")

    def test_unknown_with_safe_learning_action_uses_v2_optimizer(self):
        out = router.route(
            goal="learn new tool",
            verified_coverage=False,
            required_facts={"mechanism"},
            verified_facts=set(),
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "probe"},
                {"id": "h2", "plausible": True, "best_action": "inspect"},
            ],
            actions=[
                {"id": "search", "decision_gain": 2, "transfer_gain": 0, "proof_gain": 0, "time": 4, "cost": 0, "risk": 0},
                {"id": "probe", "decision_gain": 2, "transfer_gain": 2, "proof_gain": 2, "time": 1, "cost": 0, "risk": 0},
            ],
        )
        self.assertEqual(out["route"], "LEARN")
        self.assertEqual(out["next_action"]["id"], "probe")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_no_safe_information_action_and_disagreement_abstains(self):
        out = router.route(
            goal="choose safely",
            verified_coverage=False,
            required_facts={"hidden-state"},
            verified_facts=set(),
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "left"},
                {"id": "h2", "plausible": True, "best_action": "right"},
            ],
            actions=[],
        )
        self.assertEqual(out["route"], "ABSTAIN_OR_REQUEST_DISCRIMINATOR")
        self.assertEqual(out["reason"], "NO_SAFE_INFORMATION_ACTION_AND_LIVE_HYPOTHESES_DISAGREE")
        self.assertFalse(out["trusted_execution_authorized"])

    def test_model_uncertainty_can_be_decision_sufficient_without_becoming_trusted_knowledge(self):
        out = router.route(
            goal="choose action",
            verified_coverage=False,
            required_facts={"unknown-mechanism"},
            verified_facts=set(),
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "stop"},
                {"id": "h2", "plausible": True, "best_action": "stop"},
            ],
            actions=[],
        )
        self.assertEqual(out["route"], "DECISION_SUFFICIENT_UNVERIFIED_MODEL")
        self.assertEqual(out["recommended_action"], "stop")
        self.assertFalse(out["trusted_execution_authorized"])
        self.assertFalse(out["promotion_authorized"])

    def test_all_routes_preserve_zero_terminal_credit(self):
        out = router.route(
            goal="x",
            verified_coverage=True,
            required_facts={"a"},
            verified_facts={"a"},
            hypotheses=[],
            actions=[],
        )
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
