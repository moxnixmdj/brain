from __future__ import annotations

import unittest

from canonical.runtime import universal_active_transfer_learner_v2 as v2


class UniversalActiveTransferLearnerV2Tests(unittest.TestCase):
    def test_minimum_novelty_delta_removes_verified_structure(self):
        out = v2.minimum_novelty_delta(
            required_facts={"syntax", "types", "ownership", "borrow-checker"},
            verified_facts={"syntax", "types", "ownership"},
        )
        self.assertEqual(out["missing"], ["borrow-checker"])
        self.assertEqual(out["covered"], ["ownership", "syntax", "types"])
        self.assertAlmostEqual(out["novelty_ratio"], 0.25)

    def test_action_ranking_prefers_decision_value_per_total_cost(self):
        actions = [
            {"id": "search", "decision_gain": 5, "transfer_gain": 1, "proof_gain": 1, "time": 5, "cost": 0, "risk": 0},
            {"id": "probe", "decision_gain": 4, "transfer_gain": 2, "proof_gain": 2, "time": 1, "cost": 0, "risk": 0},
        ]
        out = v2.rank_learning_actions(actions)
        self.assertEqual(out[0]["id"], "probe")
        self.assertGreater(out[0]["value_density"], out[1]["value_density"])

    def test_action_ranking_rejects_negative_cost_dimensions(self):
        with self.assertRaises(v2.ActiveTransferLearnerError):
            v2.rank_learning_actions([
                {"id": "bad", "decision_gain": 1, "transfer_gain": 0, "proof_gain": 0, "time": -1, "cost": 0, "risk": 0}
            ])

    def test_hypothesis_update_eliminates_only_explicitly_contradicted_models(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "inspect"},
            {"id": "h2", "plausible": True, "best_action": "probe"},
            {"id": "h3", "plausible": False, "best_action": "stop"},
        ]
        out = v2.update_hypotheses(hypotheses, contradicted_ids={"h2"})
        self.assertEqual(out["live_ids"], ["h1"])
        self.assertEqual(out["eliminated_ids"], ["h2", "h3"])

    def test_decision_sufficiency_stops_when_all_live_hypotheses_choose_same_action(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "stop"},
            {"id": "h2", "plausible": True, "best_action": "stop"},
            {"id": "h3", "plausible": False, "best_action": "go"},
        ]
        out = v2.decision_sufficient(hypotheses)
        self.assertTrue(out["sufficient"])
        self.assertEqual(out["action"], "stop")

    def test_decision_sufficiency_rejects_disagreement(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "a"},
            {"id": "h2", "plausible": True, "best_action": "b"},
        ]
        out = v2.decision_sufficient(hypotheses)
        self.assertFalse(out["sufficient"])
        self.assertIsNone(out["action"])

    def test_dependency_cone_invalidates_only_descendants(self):
        deps = {
            "api-v2": ["auth-route", "upload-skill"],
            "auth-route": ["login-workflow"],
            "upload-skill": [],
            "login-workflow": [],
            "unrelated": [],
        }
        out = v2.invalidation_cone(changed={"api-v2"}, dependencies=deps)
        self.assertEqual(
            out["invalidated"],
            ["api-v2", "auth-route", "login-workflow", "upload-skill"],
        )
        self.assertNotIn("unrelated", out["invalidated"])

    def test_skill_compilation_preserves_applicability_dependencies_and_invalidators(self):
        out = v2.compile_verified_skill(
            skill_id="learn-api-schema-first",
            applicability={"unfamiliar-api"},
            dependencies={"schema-visible", "safe-read"},
            invalidators={"schema-version-changed"},
            verification_receipts={"receipt-1"},
        )
        self.assertEqual(out["status"], "VERIFIED_SKILL")
        self.assertEqual(out["dependencies"], ["safe-read", "schema-visible"])
        self.assertEqual(out["invalidators"], ["schema-version-changed"])
        self.assertFalse(out["acceptance_credit"])
        self.assertFalse(out["ownership_credit"])

    def test_meta_learning_compiles_strategy_without_promoting_unverified_claims(self):
        episode = {
            "domain": "unfamiliar-api",
            "actions": [
                {"kind": "web-search", "decision_gain": 1, "time": 5},
                {"kind": "schema-inspection", "decision_gain": 5, "time": 1},
            ],
            "verified": True,
        }
        out = v2.compile_learning_strategy(episode)
        self.assertEqual(out["preferred_action_kind"], "schema-inspection")
        self.assertFalse(out["acceptance_credit"])
        self.assertFalse(out["ownership_credit"])

    def test_unverified_episode_cannot_compile_meta_strategy(self):
        with self.assertRaises(v2.ActiveTransferLearnerError):
            v2.compile_learning_strategy({
                "domain": "x",
                "actions": [{"kind": "guess", "decision_gain": 99, "time": 0.1}],
                "verified": False,
            })

    def test_unknown_episode_remains_fail_closed_until_verified(self):
        out = v2.learning_episode(
            goal="understand new system",
            required_facts={"mechanism-x"},
            verified_facts=set(),
            hypotheses=[{"id": "h1", "plausible": True, "best_action": "inspect"}],
            actions=[{"id": "inspect", "decision_gain": 1, "transfer_gain": 0, "proof_gain": 1, "time": 1, "cost": 0, "risk": 0}],
        )
        self.assertEqual(out["state"], "LEARNING")
        self.assertFalse(out["trusted"])
        self.assertFalse(out["promotion_authorized"])
        self.assertEqual(out["next_action"]["id"], "inspect")

    def test_fully_covered_episode_uses_verified_route_without_learning(self):
        out = v2.learning_episode(
            goal="reuse known mechanism",
            required_facts={"mechanism-x"},
            verified_facts={"mechanism-x"},
            hypotheses=[],
            actions=[],
        )
        self.assertEqual(out["state"], "VERIFIED_COVERAGE")
        self.assertTrue(out["trusted"])
        self.assertTrue(out["promotion_authorized"])
        self.assertIsNone(out["next_action"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
