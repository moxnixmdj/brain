import unittest

from canonical.runtime import enforce_goal_hierarchy


class FrontierTargetMirrorTests(unittest.TestCase):
    def setUp(self):
        self.hierarchy={
            "active_capability_target":"CAP_A",
            "current_parent_blocker":"BLOCKER_A",
            "next_required_action_class":"ACTION_A",
        }
        self.target={
            "capability_id":"CAP_A",
            "residual_gap":"BLOCKER_A",
            "next_action":"ACTION_A",
        }

    def test_exact_match_passes(self):
        self.assertEqual(enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,self.target),[])

    def test_target_id_drift_fails(self):
        bad=dict(self.target); bad["capability_id"]="CAP_B"
        self.assertIn("FRONTIER_TARGET_CAPABILITY_ID_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))

    def test_blocker_drift_fails(self):
        bad=dict(self.target); bad["residual_gap"]="BLOCKER_B"
        self.assertIn("FRONTIER_TARGET_RESIDUAL_GAP_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))

    def test_next_action_drift_fails(self):
        bad=dict(self.target); bad["next_action"]="ACTION_B"
        self.assertIn("FRONTIER_TARGET_NEXT_ACTION_MISMATCH",enforce_goal_hierarchy.active_target_mirror_errors(self.hierarchy,bad))


if __name__=="__main__":
    unittest.main()
