from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_assurance_shadow_integration_v1 as shadow


class R2AssuranceShadowIntegrationV1Tests(unittest.TestCase):
    @patch.object(shadow.r2, "run")
    def test_r2_pass_is_preserved_and_v2_remains_shadow_open(self, run_r2):
        run_r2.return_value = {
            "schema": "R2",
            "status": "PASS__GOAL",
            "pass": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        out = shadow.run({"task_id": "x", "goal": "g"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["r2_pass_unchanged"])
        self.assertTrue(out["assurance_is_shadow_only"])
        self.assertEqual(
            out["assurance_result"]["status"],
            "OPEN__ADVERSARIAL_CLOSURE_REQUIRED",
        )
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    @patch.object(shadow.r2, "run")
    def test_r2_open_is_preserved_as_v2_residual(self, run_r2):
        run_r2.return_value = {
            "schema": "R2",
            "status": "OPEN__THING",
            "pass": False,
            "next_required_edge": "AUTHENTICATED_THING",
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        out = shadow.run({"task_id": "x", "goal": "g"})
        self.assertFalse(out["r2_pass_unchanged"])
        self.assertEqual(
            out["assurance_result"]["status"],
            "OPEN__ASSURANCE_RESIDUAL",
        )
        self.assertIn(
            "obligation:next-edge",
            out["assurance_result"]["open_residual_ids"],
        )
        self.assertFalse(out["terminal_authority"])

    @patch.object(shadow.r2, "run")
    def test_shadow_never_promotes_terminal_authority(self, run_r2):
        run_r2.return_value = {
            "schema": "R2",
            "status": "OPEN",
            "pass": False,
            "terminal_authority": True,
            "terminal_credit_delta": 999,
        }
        out = shadow.run({"task_id": "x", "goal": "g"})
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
