from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import general_adequate_decision_totalized_v1 as totalized


class R2TotalizedMetaActionTests(unittest.TestCase):
    def test_verified_goal_satisfaction_returns_result(self):
        out = totalized.classify(
            {"pass": True, "actual_goal_satisfaction_verified": True}
        )
        self.assertEqual(out["meta_action"], totalized.RETURN_VERIFIED_RESULT)

    def test_pass_without_goal_satisfaction_fails_closed(self):
        out = totalized.classify(
            {"pass": True, "actual_goal_satisfaction_verified": False}
        )
        self.assertEqual(out["meta_action"], totalized.ABSTAIN_FAIL_CLOSED)

    def test_information_edge_queries_only_needed_information(self):
        out = totalized.classify(
            {"pass": False, "next_information_request": {"predicate_id": "p"}}
        )
        self.assertEqual(out["meta_action"], totalized.ACQUIRE_MINIMUM_INFORMATION)

    def test_binding_gap_requests_authority_not_execution(self):
        out = totalized.classify(
            {"pass": False, "status": "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"}
        )
        self.assertEqual(out["meta_action"], totalized.ACQUIRE_AUTHORITY_BINDING)

    def test_policy_gap_repairs_cover(self):
        out = totalized.classify(
            {"pass": False, "next_policy_request": {"policy_gap": "g"}}
        )
        self.assertEqual(out["meta_action"], totalized.REPAIR_ADEQUACY_COVER)

    def test_unknown_gap_abstains(self):
        out = totalized.classify({"pass": False, "status": "FAIL_CLOSED"})
        self.assertEqual(out["meta_action"], totalized.ABSTAIN_FAIL_CLOSED)

    def test_run_totalizes_fixed_point_output_without_adding_authority(self):
        fixed = {
            "pass": False,
            "status": "OPEN__POLICY",
            "next_policy_request": {"policy_gap": "g"},
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        with patch.object(totalized.fixed_point, "run", return_value=fixed):
            out = totalized.run({"task_id": "t", "goal": "g"})
        self.assertTrue(out["r2_meta_action_totalized"])
        self.assertEqual(out["r2_meta_action"], totalized.REPAIR_ADEQUACY_COVER)
        self.assertFalse(out["r2_meta_action_execution_authority"])
        self.assertFalse(out["r2_meta_action_semantic_truth_authority"])
        self.assertFalse(out["r2_meta_action_open_world_completion_claimed"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
