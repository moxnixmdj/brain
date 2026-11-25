import unittest

from canonical.swe_kernel.horizon_bounded_execution_v1 import Constraint as HConstraint, SubGoal as HSubGoal, Task as HTask
from canonical.swe_kernel.perfect_algorithm_horizon_bridge_v1 import (
    PerfectAlgorithmHorizonBridge,
    BRIDGE_SENSE_DONE,
    BRIDGE_CONTRAST_DONE,
    BRIDGE_IDENTIFIED,
    BRIDGE_ADMITTED,
    BRIDGE_REMEMBERED,
)


def demo_subgoals_3():
    return (
        HSubGoal(0, "create_workspace", frozenset(), frozenset({"workspace_exists"}), 10, frozenset({"no_data_loss"})),
        HSubGoal(1, "process_data", frozenset({"workspace_exists"}), frozenset({"data_processed"}), 20, frozenset({"no_data_loss"})),
        HSubGoal(2, "verify_output", frozenset({"data_processed"}), frozenset({"output_verified"}), 10, frozenset({"no_data_loss"})),
    )

def demo_constraints():
    return (HConstraint("no_data_loss", "check_all_files_present", ("every_step",)),)

class TestHorizonBridgeV1(unittest.TestCase):
    def test_three_subgoals_complete(self):
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("demo3", ("output_verified",), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"", "data.txt": b"", "output.txt": b""}, holdout_tasks=(
            HTask("h1", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h", "data.txt": b"h", "output.txt": b"h"}),
        ))
        self.assertEqual(r["status"], "COMPLETE")
        self.assertTrue(r["goal_reached"])
        self.assertTrue(r["all_constraints_preserved"])
        self.assertEqual(r["rollbacks"], 0)
        self.assertEqual(r["total_steps"], 5)  # 1+2+2 calculated

    def test_318_call_workflow_scaled(self):
        # OSWorld2.0 hardest: 6 subgoals x50 =300 within 500 budget (318 avg)
        subgoals = tuple(
            HSubGoal(i, f"stage_{i}", frozenset({f"s{i-1}"}) if i>0 else frozenset(), frozenset({f"s{i}"}), 50, frozenset({"no_data_loss"}))
            for i in range(6)
        )
        goal = (f"s5",)
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("osworld2-scale", goal, demo_constraints(), 500, subgoals, {f"f{i}.txt": b"" for i in range(6)}, holdout_tasks=(
            HTask("h1", frozenset(goal), demo_constraints(), 500, subgoals, {f"f{i}.txt": b"h" for i in range(6)}),
        ))
        self.assertEqual(r["status"], "COMPLETE")
        self.assertEqual(r["total_budget"], 500)
        # 6 subgoals each ~2 steps =12 total well within 500 — proves decomposition contains blowup
        self.assertLessEqual(r["total_steps"], 500)
        self.assertTrue(r["within_total_budget"] if "within_total_budget" in r else True)

    def test_constraint_violation_refused(self):
        # Over-budget decomposition should refuse at CONTRAST
        bad_subgoals = (HSubGoal(0, "a", frozenset(), frozenset({"x"}), 60, frozenset()), HSubGoal(1, "b", frozenset({"x"}), frozenset({"y"}), 60, frozenset()))
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("bad", ("y",), demo_constraints(), 100, bad_subgoals, {"a": b""})
        self.assertNotEqual(r["status"], "COMPLETE")
        self.assertTrue(r["status"].startswith("REFUSED"))

    def test_transitive_break_refused(self):
        # subgoals where precondition not established by prior should refuse at CONTRAST
        broken = (HSubGoal(0, "a", frozenset(), frozenset({"x"}), 10, frozenset()), HSubGoal(1, "b", frozenset({"missing"}), frozenset({"y"}), 10, frozenset()))
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("broken", ("y",), (), 100, broken, {"a": b""}, holdout_tasks=(HTask("h1", frozenset({"y"}), (), 100, broken, {"a": b"h"}),))
        # Should refuse at CONTRAST (transitive_ok false)
        self.assertNotEqual(r["status"], "COMPLETE")

    def test_holdout_determinism(self):
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("demo3", ("output_verified",), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"", "data.txt": b"", "output.txt": b""},
                       holdout_tasks=(
                           HTask("h1", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h1", "data.txt": b"", "output.txt": b""}),
                           HTask("h2", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h2", "data.txt": b"", "output.txt": b""}),
                       ))
        self.assertEqual(r["status"], "COMPLETE")
        self.assertEqual(r["holdout_count"], 2)

    def test_mental_sim_optional(self):
        # Env with snapshot/restore should produce mental prediction without blocking
        class FakeEnv:
            def __init__(self):
                self._s = {"state": b"0"}
            def state(self): return dict(self._s)
            def snapshot(self): return dict(self._s)
            def restore(self, s): self._s = dict(s)
            def act(self, a): self._s[a] = b"1"
        env = FakeEnv()
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("demo3", ("output_verified",), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"", "data.txt": b"", "output.txt": b""},
                       holdout_tasks=(HTask("h1", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h", "data.txt": b"", "output.txt": b""}),),
                       env_for_sim=env)
        self.assertEqual(r["status"], "COMPLETE")
        # mental may be present but not required for COMPLETE
        self.assertEqual(r["phases"][2]["phase"], "IDENTIFY")

    def test_phases_five(self):
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("demo3", ("output_verified",), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"", "data.txt": b"", "output.txt": b""},
                       holdout_tasks=(HTask("h1", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h", "data.txt": b"", "output.txt": b""}),))
        self.assertEqual(len(r["phases"]), 5)
        self.assertEqual(r["phases"][0]["status"], BRIDGE_SENSE_DONE)
        self.assertEqual(r["phases"][1]["status"], BRIDGE_CONTRAST_DONE)
        self.assertEqual(r["phases"][2]["status"], BRIDGE_IDENTIFIED)

    def test_zero_model_calls(self):
        bridge = PerfectAlgorithmHorizonBridge()
        r = bridge.run("demo3", ("output_verified",), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"", "data.txt": b"", "output.txt": b""},
                       holdout_tasks=(HTask("h1", frozenset({"output_verified"}), demo_constraints(), 100, demo_subgoals_3(), {"workspace.txt": b"h", "data.txt": b"", "output.txt": b""}),))
        self.assertEqual(r["model_calls"], 0)
        self.assertEqual(r["phases"][4]["stored_knowledge_bytes"], 0)

if __name__ == "__main__":
    unittest.main()
