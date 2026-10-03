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

    def test_action_ranking_prefers_decision_value_per_total_cost(self):
        actions = [
            {"id": "search", "decision_gain": 5, "transfer_gain": 1, "proof_gain": 1, "time": 5, "cost": 0, "risk": 0},
            {"id": "probe", "decision_gain": 4, "transfer_gain": 2, "proof_gain": 2, "time": 1, "cost": 0, "risk": 0},
        ]
        out = v2.rank_learning_actions(actions)
        self.assertEqual(out[0]["id"], "probe")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
