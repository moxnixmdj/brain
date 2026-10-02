import unittest
from canonical.runtime.explicit_recovery_planner import RepairAction,plan_recovery

class ExplicitRecoveryPlannerTests(unittest.TestCase):
    def test_exact_cover(self):
        acts=[
          RepairAction("a",frozenset({"I1"}),cost=1,risk=.1),
          RepairAction("b",frozenset({"I2"}),cost=1,risk=.1),
          RepairAction("ab",frozenset({"I1","I2"}),cost=3,risk=0),
        ]
        o=plan_recovery({"I1","I2"},set(),acts)
        self.assertEqual(o["selected_actions"],["a","b"])
    def test_unauthorized_ignored(self):
        acts=[RepairAction("bad",frozenset({"I"}),authorized=False),RepairAction("ok",frozenset({"I"}),cost=2)]
        self.assertEqual(plan_recovery({"I"},set(),acts)["selected_actions"],["ok"])
    def test_prerequisite_gate(self):
        acts=[RepairAction("a",frozenset({"I"}),frozenset({"P"}))]
        self.assertEqual(plan_recovery({"I"},set(),acts)["status"],"ESCALATE")
        self.assertEqual(plan_recovery({"I"},{"P"},acts)["status"],"SELECT")
    def test_partial_coverage_escalates(self):
        o=plan_recovery({"I1","I2"},set(),[RepairAction("a",frozenset({"I1"}))])
        self.assertEqual(o["status"],"ESCALATE"); self.assertEqual(o["uncovered"],["I2"])
    def test_no_failures_passes(self):
        self.assertEqual(plan_recovery(set(),set(),[])["status"],"PASS")
if __name__=="__main__": unittest.main()
