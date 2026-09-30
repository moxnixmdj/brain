import unittest
from unittest.mock import patch

from canonical.runtime import enforce_goal_hierarchy


class ActiveTargetMirrorTests(unittest.TestCase):
    def setUp(self):
        self.hierarchy={
            "active_capability_target":"OPEN_ENDED_AGENTIC_TECHNICAL_RESEARCH_AND_SCIENTIFIC_PROBLEM_SOLVING_V1",
            "current_parent_blocker":"BLOCKER_A",
            "next_required_action_class":"ACTION_A",
        }
        self.target={
            "capability_id":"OPEN_ENDED_AGENTIC_TECHNICAL_RESEARCH_AND_SCIENTIFIC_PROBLEM_SOLVING_V1",
            "residual_gap":"BLOCKER_A",
            "next_action":"ACTION_A",
        }

    def test_matching_target_record_is_accepted(self):
        with patch.object(enforce_goal_hierarchy,"fail") as fail:
            enforce_goal_hierarchy.enforce_active_target_record_consistency(
                self.hierarchy,
                self.target,
            )
        fail.assert_not_called()

    def test_target_id_mismatch_fails_closed(self):
        target=dict(self.target,capability_id="WRONG_TARGET")
        with patch.object(enforce_goal_hierarchy,"fail") as fail:
            enforce_goal_hierarchy.enforce_active_target_record_consistency(
                self.hierarchy,
                target,
            )
        fail.assert_any_call("TARGET_RECORD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH")

    def test_blocker_mismatch_fails_closed(self):
        target=dict(self.target,residual_gap="WRONG_BLOCKER")
        with patch.object(enforce_goal_hierarchy,"fail") as fail:
            enforce_goal_hierarchy.enforce_active_target_record_consistency(
                self.hierarchy,
                target,
            )
        fail.assert_any_call("TARGET_RECORD_HIERARCHY_CRITICAL_BLOCKER_MISMATCH")

    def test_next_action_mismatch_fails_closed(self):
        target=dict(self.target,next_action="WRONG_ACTION")
        with patch.object(enforce_goal_hierarchy,"fail") as fail:
            enforce_goal_hierarchy.enforce_active_target_record_consistency(
                self.hierarchy,
                target,
            )
        fail.assert_any_call("TARGET_RECORD_HIERARCHY_NEXT_ACTION_MISMATCH")

    def test_missing_target_record_fails_closed(self):
        with patch.object(enforce_goal_hierarchy,"fail") as fail:
            enforce_goal_hierarchy.enforce_active_target_record_consistency(
                self.hierarchy,
                {},
            )
        fail.assert_any_call("ACTIVE_FRONTIER_TARGET_RECORD_INVALID")


if __name__=="__main__":
    unittest.main()
