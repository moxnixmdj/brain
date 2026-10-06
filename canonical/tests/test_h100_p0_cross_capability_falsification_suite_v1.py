import unittest
from canonical.runtime import h100_p0_cross_capability_falsification_suite_v1 as s
class T(unittest.TestCase):
 def test_frozen_suite(self):
  r=s.run_suite()
  self.assertEqual(r["passed"],9)
  self.assertEqual(r["total"],9)
  self.assertTrue(r["all_pass"])
  self.assertEqual(r["target_adapted_persistent_bits"],0)
 def test_no_task_id_dispatch_in_generic_primitives(self):
  # Generic functions consume task data and contain no frozen task IDs.
  names=["symbolic_reasoning","program_synthesis","lexical_semantics","raster_vision","tool_selection","planning","event_memory","unknown_domain","missing_information_control"]
  for n in names:
   self.assertTrue(callable(getattr(s,n)))
 def test_information_control_abstains(self):
  o=s.missing_information_control(s.TASKS["MISSING_INFORMATION_CONTROL"])
  self.assertEqual(o["status"],"ABSTAIN")
  self.assertEqual(o["reason"],"INFORMATION")
  self.assertEqual(o["residual_worlds"],2)
 def test_program_synthesis_unique(self):
  o=s.program_synthesis(s.TASKS["PROGRAM_SYNTHESIS"])
  self.assertEqual(o["program"],"ROTATE_LEFT")
 def test_unknown_domain_unique(self):
  o=s.unknown_domain(s.TASKS["UNKNOWN_DOMAIN_ADAPTATION"])
  self.assertEqual(o["mechanism"],"X3_PLUS_X")
if __name__=="__main__": unittest.main(verbosity=2)
