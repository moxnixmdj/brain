from __future__ import annotations

import unittest

from canonical.runtime import universal_learning_optimizer_v2 as opt


class UniversalLearningOptimizerV2Tests(unittest.TestCase):
    def test_minimum_novelty_delta_is_exact_set_difference(self):
        out = opt.minimum_novelty_delta(
            required_atoms={"parser", "ownership", "async"},
            verified_atoms={"parser", "async", "irrelevant"},
        )
        self.assertEqual(out["missing_atoms"], ["ownership"])
        self.assertEqual(out["reused_atoms"], ["async", "parser"])

    def test_transfer_requires_verified_source_and_scope_relation(self):
        good = opt.admit_transfer(
            source_id="rust-ownership",
            source_verified=True,
            scope_relation="SUPERSET",
            target_atom="ownership",
            falsifier="borrowed reference outlives owner",
        )
        self.assertTrue(good["admitted"])
        for kwargs in (
            dict(source_verified=False, scope_relation="SUPERSET", falsifier="x"),
            dict(source_verified=True, scope_relation="ANALOGOUS", falsifier="x"),
            dict(source_verified=True, scope_relation="EXACT", falsifier=""),
        ):
            with self.subTest(kwargs=kwargs):
                out = opt.admit_transfer(
                    source_id="s",
                    target_atom="t",
                    **kwargs,
                )
                self.assertFalse(out["admitted"])

    def test_action_selection_uses_conservative_value_not_point_estimates(self):
        actions = [
            {
                "id": "fast-flashy-search",
                "channel": "RETRIEVE_DIRECT_OR_INDIRECT_EVIDENCE",
                "safe": True,
                "decision_gain_lcb": 0.30,
                "future_transfer_lcb": 0.10,
                "proof_value_lcb": 0.10,
                "wall_clock_ub": 1.0,
                "cost_ub": 0.0,
                "risk_ub": 0.02,
            },
            {
                "id": "small-experiment",
                "channel": "SAFE_EXPERIMENT",
                "safe": True,
                "decision_gain_lcb": 0.70,
                "future_transfer_lcb": 0.40,
                "proof_value_lcb": 0.60,
                "wall_clock_ub": 2.0,
                "cost_ub": 0.0,
                "risk_ub": 0.01,
            },
        ]
        out = opt.choose_learning_action(actions)
        self.assertEqual(out["selected_action_id"], "small-experiment")
        self.assertEqual(out["optimization_basis"], "CONSERVATIVE_LOWER_VALUE_OVER_UPPER_BURDEN")

    def test_unsafe_action_is_never_selected_even_if_nominally_better(self):
        actions = [
            {
                "id": "unsafe-oracle",
                "channel": "OBSERVE_ENVIRONMENT",
                "safe": False,
                "decision_gain_lcb": 1.0,
                "future_transfer_lcb": 1.0,
                "proof_value_lcb": 1.0,
                "wall_clock_ub": 0.01,
                "cost_ub": 0.0,
                "risk_ub": 0.0,
            },
            {
                "id": "safe-derive",
                "channel": "DERIVE_AND_REASON",
                "safe": True,
                "decision_gain_lcb": 0.2,
                "future_transfer_lcb": 0.2,
                "proof_value_lcb": 0.2,
                "wall_clock_ub": 1.0,
                "cost_ub": 0.0,
                "risk_ub": 0.0,
            },
        ]
        out = opt.choose_learning_action(actions)
        self.assertEqual(out["selected_action_id"], "safe-derive")

    def test_decision_sufficiency_stops_when_surviving_models_agree(self):
        out = opt.decision_sufficiency(
            hypotheses=[
                {"id": "h1", "alive": True, "recommended_action": "compile", "safety_ok": True},
                {"id": "h2", "alive": True, "recommended_action": "compile", "safety_ok": True},
                {"id": "dead", "alive": False, "recommended_action": "run", "safety_ok": False},
            ]
        )
        self.assertTrue(out["decision_sufficient"])
        self.assertEqual(out["action"], "compile")

    def test_decision_sufficiency_fails_when_models_disagree_or_safety_unknown(self):
        disagree = opt.decision_sufficiency(
            hypotheses=[
                {"id": "h1", "alive": True, "recommended_action": "a", "safety_ok": True},
                {"id": "h2", "alive": True, "recommended_action": "b", "safety_ok": True},
            ]
        )
        self.assertFalse(disagree["decision_sufficient"])
        unsafe = opt.decision_sufficiency(
            hypotheses=[
                {"id": "h1", "alive": True, "recommended_action": "a", "safety_ok": False},
            ]
        )
        self.assertFalse(unsafe["decision_sufficient"])

    def test_dependency_cone_invalidation_is_minimal(self):
        graph = {
            "api-v2": ["parser-rule", "client-wrapper"],
            "parser-rule": ["task-skill"],
            "client-wrapper": ["task-skill"],
            "unrelated": ["other-skill"],
        }
        out = opt.invalidation_cone(graph=graph, changed={"api-v2"})
        self.assertEqual(
            out["invalidated"],
            ["api-v2", "client-wrapper", "parser-rule", "task-skill"],
        )
        self.assertNotIn("unrelated", out["invalidated"])
        self.assertNotIn("other-skill", out["invalidated"])

    def test_meta_learning_can_propose_but_never_self_promote(self):
        episodes = [
            {"strategy": "inspect-then-probe", "verified": True, "success": True, "wall_clock": 3.0},
            {"strategy": "inspect-then-probe", "verified": True, "success": True, "wall_clock": 2.0},
            {"strategy": "search-only", "verified": True, "success": False, "wall_clock": 1.0},
            {"strategy": "unverified-magic", "verified": False, "success": True, "wall_clock": 0.1},
        ]
        out = opt.meta_strategy_candidate(episodes)
        self.assertEqual(out["candidate_strategy"], "inspect-then-probe")
        self.assertFalse(out["promotion_authorized"])
        self.assertEqual(out["verified_episode_count"], 3)

    def test_v2_invariants_are_zero_credit_and_do_not_claim_semantic_universality(self):
        out = opt.prove_optimizer_invariants()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v1_required_as_safety_gate"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
