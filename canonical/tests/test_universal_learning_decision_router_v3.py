import unittest

from canonical.runtime import universal_learning_decision_router_v3 as v3


def receipt(rid="r"):
    return {
        "receipt_id": rid,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
    }


class V3Tests(unittest.TestCase):
    def test_cross_domain_structural_transfer_closes_literal_delta(self):
        mapping = {
            "source_primitive": "A:conservation",
            "target_primitive": "B:hidden-invariant",
            "relation": "EXACT",
            "mapping_basis": "CAUSAL_ISOMORPHISM",
            "verification_receipt": receipt("map"),
            "provenance_chain": ["A:receipt", "mapping:receipt"],
        }
        out = v3.route(
            goal="transfer",
            verified_coverage=True,
            required_facts={"B:hidden-invariant"},
            verified_facts={"A:conservation"},
            transfer_mappings=[mapping],
            hypotheses=[],
            actions=[],
        )
        self.assertEqual(out["route"], "USE_VERIFIED_CAPABILITY")
        self.assertEqual(out["novelty_delta"]["missing"], [])

    def test_surface_only_transfer_forbidden(self):
        with self.assertRaises(v3.LearningDecisionRouterError):
            v3.admit_structural_transfer(
                {
                    "source_primitive": "A:x",
                    "target_primitive": "B:x",
                    "relation": "EXACT",
                    "mapping_basis": "LABEL_MATCH",
                    "verification_receipt": receipt(),
                    "provenance_chain": ["p"],
                }
            )

    def test_unverified_source_cannot_transfer(self):
        with self.assertRaises(v3.LearningDecisionRouterError):
            v3.verified_coverage_with_transfers(
                verified_facts=set(),
                transfer_mappings=[
                    {
                        "source_primitive": "A:x",
                        "target_primitive": "B:y",
                        "relation": "EXACT",
                        "mapping_basis": "STRUCTURAL_EQUIVALENCE",
                        "verification_receipt": receipt(),
                        "provenance_chain": ["p"],
                    }
                ],
            )

    def test_decision_sufficiency_precedes_unnecessary_probe(self):
        out = v3.route(
            goal="stop early",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=[
                {
                    "id": "h1",
                    "plausible": True,
                    "best_action": "STOP",
                    "probability": "1/2",
                },
                {
                    "id": "h2",
                    "plausible": True,
                    "best_action": "STOP",
                    "probability": "1/2",
                },
            ],
            actions=[
                {
                    "id": "expensive",
                    "safe": True,
                    "outcome_by_hypothesis": {"h1": "a", "h2": "b"},
                    "time": 100,
                    "cost": 0,
                    "risk": 0,
                }
            ],
        )
        self.assertEqual(out["route"], "DECISION_SUFFICIENT_UNVERIFIED_MODEL")
        self.assertIsNone(out["next_action"])

    def test_decision_gain_is_derived_not_caller_claimed(self):
        ranked = v3.rank_discriminating_actions(
            hypotheses=[
                {
                    "id": "h1",
                    "plausible": True,
                    "best_action": "A",
                    "probability": "1/2",
                },
                {
                    "id": "h2",
                    "plausible": True,
                    "best_action": "B",
                    "probability": "1/2",
                },
            ],
            actions=[
                {
                    "id": "fake",
                    "safe": True,
                    "outcome_by_hypothesis": {"h1": "same", "h2": "same"},
                    "decision_gain": 999,
                    "time": 1,
                    "cost": 0,
                    "risk": 0,
                },
                {
                    "id": "real",
                    "safe": True,
                    "outcome_by_hypothesis": {"h1": "left", "h2": "right"},
                    "decision_gain": 0,
                    "time": 1,
                    "cost": 0,
                    "risk": 0,
                },
            ],
        )
        self.assertEqual([x["id"] for x in ranked], ["real"])
        self.assertEqual(ranked[0]["derived_decision_gain"], "1/2")

    def test_unsafe_or_nondiscriminating_action_cannot_prevent_abstention(self):
        out = v3.route(
            goal="uncertain",
            verified_coverage=False,
            required_facts={"x"},
            verified_facts=set(),
            transfer_mappings=[],
            hypotheses=[
                {
                    "id": "h1",
                    "plausible": True,
                    "best_action": "A",
                    "probability": "1/2",
                },
                {
                    "id": "h2",
                    "plausible": True,
                    "best_action": "B",
                    "probability": "1/2",
                },
            ],
            actions=[
                {
                    "id": "unsafe",
                    "safe": False,
                    "outcome_by_hypothesis": {"h1": "l", "h2": "r"},
                    "time": 1,
                    "cost": 0,
                    "risk": 0,
                },
                {
                    "id": "useless",
                    "safe": True,
                    "outcome_by_hypothesis": {"h1": "same", "h2": "same"},
                    "transfer_gain": 100,
                    "proof_gain": 100,
                    "time": 1,
                    "cost": 0,
                    "risk": 0,
                },
            ],
        )
        self.assertEqual(out["route"], "ABSTAIN_OR_REQUEST_DISCRIMINATOR")

    def test_probability_weighting_changes_gain(self):
        ranked = v3.rank_discriminating_actions(
            hypotheses=[
                {
                    "id": "h1",
                    "plausible": True,
                    "best_action": "A",
                    "probability": "9/10",
                },
                {
                    "id": "h2",
                    "plausible": True,
                    "best_action": "B",
                    "probability": "1/10",
                },
            ],
            actions=[
                {
                    "id": "perfect",
                    "safe": True,
                    "outcome_by_hypothesis": {"h1": "l", "h2": "r"},
                    "time": 1,
                    "cost": 0,
                    "risk": 0,
                }
            ],
        )
        self.assertEqual(ranked[0]["derived_decision_gain"], "1/10")

    def test_meta_policy_requires_matched_no_regression(self):
        episodes = [
            {
                "task_id": "t1",
                "strategy_id": "old",
                "verified": True,
                "success": True,
                "safety_violation": False,
                "wall_clock": 10,
                "reality_calls": 2,
                "information_actions": 5,
            },
            {
                "task_id": "t2",
                "strategy_id": "old",
                "verified": True,
                "success": True,
                "safety_violation": False,
                "wall_clock": 10,
                "reality_calls": 2,
                "information_actions": 5,
            },
            {
                "task_id": "t1",
                "strategy_id": "new",
                "verified": True,
                "success": True,
                "safety_violation": False,
                "wall_clock": 6,
                "reality_calls": 1,
                "information_actions": 4,
            },
            {
                "task_id": "t2",
                "strategy_id": "new",
                "verified": True,
                "success": True,
                "safety_violation": False,
                "wall_clock": 7,
                "reality_calls": 1,
                "information_actions": 4,
            },
        ]
        comparison = v3.compare_learning_strategies(
            episodes=episodes,
            incumbent="old",
            candidate="new",
        )
        self.assertTrue(comparison["preference_admissible"])
        policy = v3.compile_metacognitive_policy(
            environment_class="unseen-api",
            comparison=comparison,
            candidate_strategy="new",
            verification_receipt=receipt("meta"),
        )
        self.assertEqual(policy["scope"], "MATCHED_VERIFIED_ENVIRONMENT_CLASS_ONLY")
        self.assertFalse(policy["promotion_authorized"])

    def test_meta_success_regression_blocks_even_if_faster(self):
        episodes = [
            {
                "task_id": "t",
                "strategy_id": "old",
                "verified": True,
                "success": True,
                "safety_violation": False,
                "wall_clock": 10,
                "reality_calls": 2,
                "information_actions": 5,
            },
            {
                "task_id": "t",
                "strategy_id": "new",
                "verified": True,
                "success": False,
                "safety_violation": False,
                "wall_clock": 1,
                "reality_calls": 0,
                "information_actions": 1,
            },
        ]
        comparison = v3.compare_learning_strategies(
            episodes=episodes,
            incumbent="old",
            candidate="new",
        )
        self.assertFalse(comparison["preference_admissible"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
