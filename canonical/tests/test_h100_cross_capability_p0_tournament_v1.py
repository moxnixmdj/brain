import json, unittest
from canonical.runtime import h100_cross_capability_p0_tournament_v1 as t
class T(unittest.TestCase):
 def test_suite_precommit_has_nine_distinct_tasks(self):
  s=json.loads(t.PRE.read_text()); self.assertEqual(len(s["tasks"]),9); self.assertEqual(len({x["family"] for x in s["tasks"]}),9)
 def test_p0_nonsealed(self):
  r=t.run(); self.assertEqual(r["nonsealed_passed"],8); self.assertEqual(r["nonsealed_total"],8)
 def test_sealed_information_control(self):
  r=t.run(); x=[z for z in r["task_results"] if z["family"]=="SEALED_INFORMATION_CONTROL"][0]
  self.assertTrue(x["pass"]); self.assertEqual(x["failure_class"],"INFORMATION_GAP"); self.assertEqual(x["persistent_target_lower_bound_bits"],1)
 def test_zero_target_adapted_bits(self):
  self.assertEqual(t.run()["target_adapted_persistent_bits"],0)
 def test_generic_code_reported(self):
  self.assertGreater(t.run()["generic_frozen_runtime_code_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
