from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import general_adequate_decision_controller_v1 as controller


class GeneralDecisionAuthenticatedAdequacyBridgeTests(unittest.TestCase):
    @staticmethod
    def _raw_contract():
        return {
            "pass": True,
            "task_contract_sha256": "raw-contract",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [{"obligation_id": "RAWREQ:o1"}],
            },
        }

    @staticmethod
    def _specialist():
        return {
            "pass": True,
            "status": "PASS__SELF_AUTHENTICATING_ADEQUATE_POLICY_DISCOVERED",
            "authority_id": "AUTH",
            "policy_id": "policy.p",
            "scope_membership_verified": True,
            "selected_policy_adequacy_verified": True,
            "policy_selection_authorized": True,
            "realization": {
                "kind": "AUTHENTICATED_SPECIALIST_POLICY_RESULT",
                "authority_id": "AUTH",
                "policy_id": "policy.p",
                "result": {"x": 1},
            },
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
        }

    @patch.object(controller, "evaluate_p3")
    @patch.object(controller, "discover_authenticated_adequacy")
    @patch.object(controller, "compile_contract")
    def test_specialist_adequacy_shortcuts_p3_but_not_final_acceptance(
        self, compile_contract, discover, p3
    ):
        compile_contract.return_value = self._raw_contract()
        discover.return_value = self._specialist()
        out = controller.run({"task_id": "T", "goal": "raw goal"})
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED")
        self.assertEqual(
            out["next_required_edge"],
            "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
        )
        self.assertEqual(out["selected_policy_id"], "policy.p")
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        p3.assert_not_called()

    @patch.object(controller, "evaluate_p3")
    @patch.object(controller, "_authenticate_goal_satisfaction_binding")
    @patch.object(controller, "discover_authenticated_adequacy")
    @patch.object(controller, "compile_contract")
    def test_specialist_adequacy_closes_only_with_independent_goal_acceptance(
        self, compile_contract, discover, accept, p3
    ):
        compile_contract.return_value = self._raw_contract()
        discover.return_value = self._specialist()
        accept.return_value = {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
        }
        out = controller.run({
            "task_id": "T",
            "goal": "raw goal",
            "goal_satisfaction_binding": {"receipt": {}, "verification": {}},
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__GOAL_BOUND_AUTHENTICATED_SPECIALIST_POLICY_REALIZED_AND_ACCEPTANCE_VERIFIED",
        )
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])
        p3.assert_not_called()

    @patch.object(controller, "discover_authenticated_adequacy")
    @patch.object(controller, "compile_contract")
    @patch.object(controller, "evaluate_p3")
    def test_no_specialist_match_falls_through_to_opaque_general_reasoning(
        self, p3, compile_contract, discover
    ):
        compile_contract.return_value = self._raw_contract()
        discover.return_value = {
            "pass": False,
            "status": "UNRESOLVED__NO_SELF_AUTHENTICATING_ADEQUACY_AUTHORITY_MATCHED",
            "policy_selection_authorized": False,
            "selected_policy_adequacy_verified": False,
            "terminal_authority": False,
        }
        p3.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHENTICATED_POLICY_COVER_INCOMPLETE",
        }
        out = controller.run({"task_id": "T", "goal": "raw goal"})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"], "OPEN__ADEQUATE_POLICY_OR_SEMANTIC_COVERAGE_REQUIRED"
        )
        p3.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
