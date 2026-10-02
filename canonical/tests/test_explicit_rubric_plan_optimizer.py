import unittest
from canonical.runtime.explicit_rubric_plan_optimizer import Plan,select_plan

class ExplicitRubricPlanOptimizerTests(unittest.TestCase):
    def test_best_supported_plan_selected(self):
        w={"accuracy":2,"clarity":1}
        ps=[Plan("a",{"accuracy":.8,"clarity":.9},cost=2),Plan("b",{"accuracy":.9,"clarity":.8},cost=3)]
        self.assertEqual(select_plan(w,ps)["plan_id"],"b")
    def test_unsupported_high_score_rejected(self):
        o=select_plan({"q":1},[Plan("bad",{"q":1},evidence_supported=False),Plan("ok",{"q":.5})])
        self.assertEqual(o["plan_id"],"ok")
    def test_hard_violation_rejected(self):
        o=select_plan({"q":1},[Plan("bad",{"q":1},hard_violations=frozenset({"unsupported_claim"})),Plan("ok",{"q":.4})])
        self.assertEqual(o["plan_id"],"ok")
    def test_missing_dimension_escalates(self):
        self.assertEqual(select_plan({"a":1,"b":1},[Plan("x",{"a":1})])["status"],"ESCALATE")
    def test_exact_tie_escalates(self):
        o=select_plan({"q":1},[Plan("a",{"q":1},cost=1),Plan("b",{"q":1},cost=1)])
        self.assertEqual(o["reason"],"EXACT_RUBRIC_AND_COST_TIE")
if __name__=="__main__": unittest.main()
