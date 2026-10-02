from __future__ import annotations

import inspect
import json
import unittest

from canonical.runtime import browser_goal_grounding_recovery_candidate as candidate
from canonical.runtime import browser_goal_grounding_recovery_proof as proof


class BrowserGoalGroundingRecoveryTests(unittest.TestCase):
    def test_oracle_and_target_identity_never_enter_public_payload(self):
        case = proof.generate_case(4401, 0)
        p1 = proof.public_stage(case, 1)
        self.assertNotIn("_oracle", p1)
        self.assertNotIn("target_id", json.dumps(p1).lower())
        first = candidate.solve(p1)
        p2 = proof.public_stage(case, 2, previous_action=first)
        self.assertNotIn("_oracle", p2)
        self.assertNotIn(case["_oracle"]["target_ids"][1], json.dumps(p1))

    def test_candidate_does_not_import_evaluator(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("browser_goal_grounding_recovery_proof", src)
        self.assertNotIn("_oracle", src)

    def test_all_goal_classes_and_stale_recovery_pass(self):
        out = proof.run_batch(20261002, 60, candidate.solve)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(set(out["by_class"]), {
            "OPEN_SETTINGS", "ENABLE_FEATURE", "SEARCH_QUERY"
        })

    def test_open_settings_ignores_wrong_role_and_hidden_decoys(self):
        case = proof.generate_case(551, 0)
        p1 = proof.public_stage(case, 1)
        out = candidate.solve(p1)
        self.assertEqual(out["status"], "SELECT")
        self.assertEqual(out["element_id"], case["_oracle"]["target_ids"][0])

    def test_search_preserves_typed_value(self):
        case = proof.generate_case(552, 2)
        out = candidate.solve(proof.public_stage(case, 1))
        self.assertEqual(out["action"], "type")
        self.assertEqual(out["value"], case["_oracle"]["value"])

    def test_stale_state_requires_new_element_identity(self):
        case = proof.generate_case(553, 1)
        first = candidate.solve(proof.public_stage(case, 1))
        second = candidate.solve(proof.public_stage(case, 2, previous_action=first))
        self.assertNotEqual(first["element_id"], second["element_id"])
        self.assertEqual(second["observed_receipt_kind"], "STALE_RENDER_STATE")
        self.assertTrue(proof.score_episode(case, candidate.solve)["pass"])

    def test_replaying_old_element_fails(self):
        case = proof.generate_case(554, 0)
        calls = {"n": 0}
        first = candidate.solve(proof.public_stage(case, 1))
        def bad(public):
            calls["n"] += 1
            if calls["n"] == 1:
                return dict(first)
            out = dict(first)
            out["observed_receipt_kind"] = "STALE_RENDER_STATE"
            return out
        verdict = proof.score_episode(case, bad)
        self.assertEqual(verdict["reason"], "STALE_ELEMENT_ID_REPLAYED")

    def test_wrong_goal_action_fails(self):
        case = proof.generate_case(555, 2)
        def bad(public):
            return {
                "status": "SELECT",
                "element_id": case["_oracle"]["target_ids"][public["stage"] - 1],
                "action": "click",
                "value": None,
                "observed_receipt_kind": (public.get("receipt") or {}).get("kind"),
            }
        self.assertFalse(proof.score_episode(case, bad)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
