from __future__ import annotations
import unittest
from canonical.runtime.terminal_delta_admission_gate_v1 import evaluate

BASE={
 "unresolved_atomic_predicates":31,
 "accepted_families":2,
 "minimum_remaining_work_lower_bound":40,
 "proved_impossible_branches":["TB4_FROZEN_ROUTE"],
 "formally_owned_domain_atoms":["D1"],
 "protected_terminal_facts":["F1","F2"],
}
class Tests(unittest.TestCase):
 def test_rejects_no_delta(self):
  o=evaluate(BASE,dict(BASE),blocker_ids=["P1"])
  self.assertFalse(o["admit"]); self.assertEqual(o["status"],"PASS__REJECT_NO_TERMINAL_DELTA")
 def test_admits_residual_reduction(self):
  a=dict(BASE); a["unresolved_atomic_predicates"]=30
  self.assertTrue(evaluate(BASE,a,blocker_ids=["A"])["admit"])
 def test_admits_proved_impossibility(self):
  a=dict(BASE); a["proved_impossible_branches"]=["TB4_FROZEN_ROUTE","X"]
  self.assertTrue(evaluate(BASE,a,blocker_ids=["X"])["admit"])
 def test_admits_owned_domain_expansion(self):
  a=dict(BASE); a["formally_owned_domain_atoms"]=["D1","D2"]
  self.assertTrue(evaluate(BASE,a,blocker_ids=["D2"])["admit"])
 def test_blocks_regression_even_with_gain(self):
  a=dict(BASE); a["accepted_families"]=3; a["protected_terminal_facts"]=["F1"]
  o=evaluate(BASE,a,blocker_ids=["X"])
  self.assertFalse(o["admit"]); self.assertIn("PROTECTED_TERMINAL_FACT_LOST",o["regressions"])
 def test_requires_blocker(self):
  self.assertFalse(evaluate(BASE,BASE,blocker_ids=[])["admit"])
 def test_zero_authority(self):
  a=dict(BASE); a["minimum_remaining_work_lower_bound"]=39
  o=evaluate(BASE,a,blocker_ids=["X"])
  self.assertEqual(o["capability_credit_delta"],0); self.assertFalse(o["execution_authority"])
if __name__=="__main__": unittest.main(verbosity=2)
