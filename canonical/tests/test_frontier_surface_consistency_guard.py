import copy
import unittest

from canonical.runtime import enforce_goal_hierarchy as guard


ACTIVE="OPEN_ENDED_AGENTIC_TECHNICAL_RESEARCH_AND_SCIENTIFIC_PROBLEM_SOLVING_V1"
BLOCKER="PARENT_MODEL_INDEPENDENT_CROSS_DOMAIN_REAL_TASK_B_REQUIRED__OLD_SPACE_CARGO_TASK_A_INADMISSIBLE_FOR_DEPENDENCY_REMOVAL"
NEXT="RUN_ONE_NEW_CROSS_DOMAIN_MODEL_INDEPENDENT_PARENT_REAL_TASK_B__NO_DEMOGRAPHY_ASTRONOMY_GEOPHYSICS_BIOPHYSICS_REPLAY__STOP_ON_FIRST_NEW_CAUSAL_GAP"


def valid_surfaces():
    return (
        {"current_frontier":{
            "active_capability_target":ACTIVE,
            "critical_blocker":BLOCKER,
            "highest_leverage_capability_gap":BLOCKER,
            "next_step":NEXT,
        }},
        {
            "active_capability_target":ACTIVE,
            "current_parent_blocker":BLOCKER,
            "next_required_action_class":NEXT,
        },
        {"immediate_frontier":{
            "selected_capability":ACTIVE,
            "exact_blocker":BLOCKER,
            "next_action":NEXT,
        }},
        {
            "next_progress_event_target":NEXT,
            "active_frontier_accounting":{"parent_frontier_capability":ACTIVE},
        },
        {
            "capability_id":ACTIVE,
            "residual_gap":BLOCKER,
            "next_action":NEXT,
        },
    )


class FrontierSurfaceConsistencyGuardTests(unittest.TestCase):
    def run_guard(self, surfaces):
        guard.FAIL.clear()
        guard.enforce_frontier_surface_consistency(*surfaces)
        return list(guard.FAIL)

    def test_current_canonical_shape_passes(self):
        self.assertEqual(self.run_guard(valid_surfaces()), [])

    def test_each_authoritative_mirror_fails_closed_on_drift(self):
        cases=[
            (0, ("current_frontier","active_capability_target"), "wrong", "POINTER_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH"),
            (0, ("current_frontier","critical_blocker"), "wrong", "POINTER_HIERARCHY_CRITICAL_BLOCKER_MISMATCH"),
            (0, ("current_frontier","highest_leverage_capability_gap"), "wrong", "POINTER_HIERARCHY_HIGHEST_LEVERAGE_GAP_MISMATCH"),
            (0, ("current_frontier","next_step"), "wrong", "POINTER_HIERARCHY_NEXT_ACTION_MISMATCH"),
            (2, ("immediate_frontier","selected_capability"), "wrong", "QUEUE_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH"),
            (2, ("immediate_frontier","exact_blocker"), "wrong", "QUEUE_HIERARCHY_CRITICAL_BLOCKER_MISMATCH"),
            (2, ("immediate_frontier","next_action"), "wrong", "QUEUE_HIERARCHY_NEXT_ACTION_MISMATCH"),
            (4, ("capability_id",), "wrong", "TARGET_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH"),
            (4, ("residual_gap",), "wrong", "TARGET_HIERARCHY_CRITICAL_BLOCKER_MISMATCH"),
            (4, ("next_action",), "wrong", "TARGET_HIERARCHY_NEXT_ACTION_MISMATCH"),
            (3, ("active_frontier_accounting","parent_frontier_capability"), "wrong", "SCOREBOARD_HIERARCHY_ACTIVE_CAPABILITY_TARGET_MISMATCH"),
            (3, ("next_progress_event_target",), "wrong", "SCOREBOARD_HIERARCHY_NEXT_ACTION_MISMATCH"),
        ]
        for idx,path,value,expected in cases:
            with self.subTest(expected=expected):
                surfaces=list(copy.deepcopy(valid_surfaces()))
                node=surfaces[idx]
                for key in path[:-1]:
                    node=node[key]
                node[path[-1]]=value
                self.assertIn(expected,self.run_guard(tuple(surfaces)))


if __name__=="__main__":
    unittest.main()
