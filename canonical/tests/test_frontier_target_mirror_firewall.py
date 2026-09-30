import copy
import importlib.util
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
GUARD_PATH=ROOT/"canonical"/"runtime"/"enforce_goal_hierarchy.py"

spec=importlib.util.spec_from_file_location("frontier_target_mirror_guard",GUARD_PATH)
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.ROOT=ROOT

HIERARCHY_PATH=ROOT/"canonical"/"governance"/"ACTIVE_GOAL_HIERARCHY_V1.json"

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

class FrontierTargetMirrorTests(unittest.TestCase):
    def setUp(self):
        guard.FAIL.clear()
        self.hierarchy=load_json(HIERARCHY_PATH)
        target_id=self.hierarchy["active_capability_target"]
        self.target=load_json(
            ROOT/"canonical"/"capabilities"/"frontier"/(target_id+".json")
        )

    def test_current_target_record_matches_active_frontier(self):
        guard.enforce_active_target_record_consistency(
            self.hierarchy,self.target
        )
        self.assertEqual(guard.FAIL,[])

    def test_target_identity_drift_fails_closed(self):
        bad=copy.deepcopy(self.target)
        bad["capability_id"]="STALE_CAPABILITY"
        guard.enforce_active_target_record_consistency(self.hierarchy,bad)
        self.assertIn(
            "TARGET_RECORD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH",
            guard.FAIL,
        )

    def test_target_blocker_drift_fails_closed(self):
        bad=copy.deepcopy(self.target)
        bad["residual_gap"]="STALE_BLOCKER"
        guard.enforce_active_target_record_consistency(self.hierarchy,bad)
        self.assertIn(
            "TARGET_RECORD_HIERARCHY_CRITICAL_BLOCKER_MISMATCH",
            guard.FAIL,
        )

    def test_target_next_action_drift_fails_closed(self):
        bad=copy.deepcopy(self.target)
        bad["next_action"]="STALE_NEXT_ACTION"
        guard.enforce_active_target_record_consistency(self.hierarchy,bad)
        self.assertIn(
            "TARGET_RECORD_HIERARCHY_NEXT_ACTION_MISMATCH",
            guard.FAIL,
        )

if __name__=="__main__":
    unittest.main()
