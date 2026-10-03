from __future__ import annotations

import unittest

from canonical.runtime import dependency_superset_delta_v5 as delta5
from canonical.runtime import recursive_abstraction_v5 as abs5
from canonical.runtime import compounding_probe_rank_v5 as rank5
from canonical.runtime import universal_learning_recursive_abstraction_router_v5 as router5


def dependency_receipt(*, env, goal, goals, graph, relation="PROVEN_SUPERSET"):
    return {
        "receipt_id": "dep-r1",
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "environment_id": env,
        "goal_id": goal,
        "scope_relation": relation,
        "all_true_decision_relevant_dependencies_contained": True,
        "dependency_graph_sha256": delta5.dependency_digest(goals=goals, dependencies=graph),
    }


def safety_receipt(env, goal, action_id):
    return {
        "receipt_id": "safe-" + action_id,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "safe_under_all_admissible_worlds": True,
        "environment_id": env,
        "goal_id": goal,
        "action_id": action_id,
    }


def skill(skill_id, signature):
    digest = abs5.signature_digest(signature)
    return {
        "skill_id": skill_id,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "canonical_signature": signature,
        "canonicalization_receipt": {
            "receipt_id": "canon-" + skill_id,
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "skill_id": skill_id,
            "signature_sha256": digest,
            "mapping_basis": "FORMAL_REDUCTION",
        },
    }


class DependencySupersetDeltaV5Tests(unittest.TestCase):
    def test_proven_superset_can_safely_shrink_flat_environment_learning(self):
        graph = {"goal": ["known", "needed", "extra"], "needed": ["deep"]}
        receipt = dependency_receipt(
            env="env",
            goal="goal-id",
            goals=["goal"],
            graph=graph,
            relation="PROVEN_SUPERSET",
        )
        out = delta5.goal_delta_upper_bound(
            environment_id="env",
            goal_id="goal-id",
            goals=["goal"],
            verified_facts=["known"],
            dependencies=graph,
            dependency_receipt=receipt,
        )
        self.assertEqual(out["scope_relation"], "PROVEN_SUPERSET")
        self.assertTrue(out["sound_upper_bound_on_required_novelty"])
        self.assertFalse(out["minimality_proved"])
        self.assertEqual(out["verified_boundary"], ["known"])
        self.assertEqual(out["missing"], ["deep", "extra", "goal", "needed"])
        self.assertTrue(out["safe_to_prune_outside_reachable_graph"])

    def test_exact_relation_marks_minimality_proved(self):
        graph = {"goal": ["needed"]}
        receipt = dependency_receipt(
            env="env", goal="g", goals=["goal"], graph=graph, relation="EXACT"
        )
        out = delta5.goal_delta_upper_bound(
            environment_id="env",
            goal_id="g",
            goals=["goal"],
            verified_facts=[],
            dependencies=graph,
            dependency_receipt=receipt,
        )
        self.assertTrue(out["minimality_proved"])

    def test_analogy_or_unproved_soundness_fails_closed(self):
        graph = {"goal": ["needed"]}
        bad = dependency_receipt(
            env="env", goal="g", goals=["goal"], graph=graph, relation="ANALOGOUS"
        )
        with self.assertRaises(delta5.DependencySupersetDeltaError):
            delta5.goal_delta_upper_bound(
                environment_id="env",
                goal_id="g",
                goals=["goal"],
                verified_facts=[],
                dependencies=graph,
                dependency_receipt=bad,
            )
        bad = dependency_receipt(
            env="env", goal="g", goals=["goal"], graph=graph
        )
        bad["all_true_decision_relevant_dependencies_contained"] = False
        with self.assertRaises(delta5.DependencySupersetDeltaError):
            delta5.goal_delta_upper_bound(
                environment_id="env",
                goal_id="g",
                goals=["goal"],
                verified_facts=[],
                dependencies=graph,
                dependency_receipt=bad,
            )


class RecursiveAbstractionV5Tests(unittest.TestCase):
    def test_common_verified_structure_becomes_candidate_not_truth(self):
        a = skill("a", ["control:branch", "data:map", "io:file"])
        b = skill("b", ["control:branch", "data:map", "net:http"])
        out = abs5.induce_candidate([a, b])
        self.assertEqual(out["common_signature"], ["control:branch", "data:map"])
        self.assertFalse(out["verified_abstraction"])
        self.assertFalse(out["promotion_authorized"])
        self.assertTrue(out["separate_abstraction_verification_required"])

    def test_unverified_or_unbound_skill_cannot_seed_abstraction(self):
        a = skill("a", ["x", "y"])
        b = skill("b", ["x", "z"])
        b["independent_verified"] = False
        with self.assertRaises(abs5.RecursiveAbstractionError):
            abs5.induce_candidate([a, b])

    def test_external_receipt_can_verify_candidate_without_acceptance_credit(self):
        candidate = abs5.induce_candidate([
            skill("a", ["x", "y"]),
            skill("b", ["x", "z"]),
        ])
        receipt = {
            "receipt_id": "abs-r1",
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "candidate_sha256": candidate["candidate_sha256"],
            "source_skill_ids": candidate["source_skill_ids"],
            "behavior_preserving_across_source_skills": True,
            "scope_relation": "PROVEN_SUPERSET",
        }
        out = abs5.verify_candidate(candidate=candidate, verification_receipt=receipt)
        self.assertTrue(out["verified_abstraction"])
        self.assertTrue(out["structural_reuse_authorized"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])


class CompoundingProbeRankV5Tests(unittest.TestCase):
    def test_primary_minimax_gain_always_beats_secondary_compounding_value(self):
        env, goal = "env", "goal"
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "a"},
            {"id": "h2", "plausible": True, "best_action": "b"},
            {"id": "h3", "plausible": True, "best_action": "c"},
        ]
        actions = [
            {
                "id": "primary-best",
                "safety_receipt": safety_receipt(env, goal, "primary-best"),
                "outcome_by_hypothesis": {"h1": "1", "h2": "2", "h3": "3"},
                "time": 2,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 0,
                "proof_value_lcb": 0,
                "future_burden_ub": 10,
            },
            {
                "id": "secondary-flashy",
                "safety_receipt": safety_receipt(env, goal, "secondary-flashy"),
                "outcome_by_hypothesis": {"h1": "1", "h2": "1", "h3": "2"},
                "time": 1,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 100,
                "proof_value_lcb": 100,
                "future_burden_ub": 0,
            },
        ]
        out = rank5.rank(
            environment_id=env,
            goal_id=goal,
            hypotheses=hypotheses,
            actions=actions,
        )
        self.assertEqual(out["ranked"][0]["id"], "primary-best")
        self.assertEqual(out["ranking_order"][0], "MINIMAX_ACTION_CLASS_REDUCTION_DESC")

    def test_secondary_compounding_value_breaks_primary_ties(self):
        env, goal = "env", "goal"
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "a"},
            {"id": "h2", "plausible": True, "best_action": "b"},
        ]
        actions = [
            {
                "id": "future-rich",
                "safety_receipt": safety_receipt(env, goal, "future-rich"),
                "outcome_by_hypothesis": {"h1": "1", "h2": "2"},
                "time": 1,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 0.8,
                "proof_value_lcb": 0.6,
                "future_burden_ub": 1,
            },
            {
                "id": "future-poor",
                "safety_receipt": safety_receipt(env, goal, "future-poor"),
                "outcome_by_hypothesis": {"h1": "x", "h2": "y"},
                "time": 1,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 0.1,
                "proof_value_lcb": 0.1,
                "future_burden_ub": 1,
            },
        ]
        out = rank5.rank(
            environment_id=env,
            goal_id=goal,
            hypotheses=hypotheses,
            actions=actions,
        )
        self.assertEqual(out["ranked"][0]["id"], "future-rich")

    def test_v4_current_value_density_precedes_future_compounding_tiebreak(self):
        env, goal = "env", "goal"
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "a"},
            {"id": "h2", "plausible": True, "best_action": "b"},
        ]
        actions = [
            {
                "id": "current-efficient",
                "safety_receipt": safety_receipt(env, goal, "current-efficient"),
                "outcome_by_hypothesis": {"h1": "1", "h2": "2"},
                "time": 1,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 0,
                "proof_value_lcb": 0,
                "future_burden_ub": 10,
            },
            {
                "id": "future-flashy-but-slow",
                "safety_receipt": safety_receipt(env, goal, "future-flashy-but-slow"),
                "outcome_by_hypothesis": {"h1": "x", "h2": "y"},
                "time": 2,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0,
                "future_transfer_lcb": 100,
                "proof_value_lcb": 100,
                "future_burden_ub": 0,
            },
        ]
        out = rank5.rank(
            environment_id=env,
            goal_id=goal,
            hypotheses=hypotheses,
            actions=actions,
        )
        self.assertEqual(out["ranked"][0]["id"], "current-efficient")
        self.assertEqual(out["ranking_order"][1], "V4_CURRENT_VALUE_DENSITY_DESC")

    def test_positive_incremental_spend_is_rejected(self):
        env, goal = "env", "goal"
        out = rank5.rank(
            environment_id=env,
            goal_id=goal,
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "a"},
                {"id": "h2", "plausible": True, "best_action": "b"},
            ],
            actions=[{
                "id": "paid",
                "safety_receipt": safety_receipt(env, goal, "paid"),
                "outcome_by_hypothesis": {"h1": "1", "h2": "2"},
                "time": 1,
                "cost": 0,
                "risk": 0,
                "incremental_spend_usd_ub": 0.01,
                "future_transfer_lcb": 1,
                "proof_value_lcb": 1,
                "future_burden_ub": 0,
            }],
        )
        self.assertEqual(out["ranked"], [])
        self.assertEqual(out["rejected"][0]["reason"], "POSITIVE_INCREMENTAL_SPEND_FORBIDDEN")


class UniversalLearningRouterV5Tests(unittest.TestCase):
    def test_unrelated_verified_skills_do_not_block_primary_learning_route(self):
        a = skill("a", ["only-a"])
        b = skill("b", ["only-b"])
        out = router5.route(
            goal="g",
            environment_id="env",
            verified_coverage=True,
            goal_facts=[],
            fallback_required_facts=[],
            verified_facts=[],
            dependencies={},
            dependency_receipt=None,
            transfer_mappings=[],
            hypotheses=[],
            hypothesis_coverage_receipt=None,
            residual_action_receipt=None,
            actions=[],
            verified_skills=[a, b],
        )
        self.assertEqual(out["route"], "USE_VERIFIED_CAPABILITY")
        self.assertIsNone(out["abstraction_candidate"])
        self.assertEqual(out["abstraction_candidate_status"], "NO_COMMON_VERIFIED_STRUCTURE")

    def test_v5_invariants_preserve_v4_open_world_safety_and_zero_credit(self):
        out = router5.prove_v5_invariants()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["v4_open_world_guard_preserved"])
        self.assertTrue(out["dependency_superset_pruning_sound"])
        self.assertTrue(out["abstraction_induction_candidate_only"])
        self.assertTrue(out["minimax_primary_order_preserved"])
        self.assertFalse(out["semantic_success_rate_proved"])
        self.assertFalse(out["unknown_domain_acceptance_proved"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
