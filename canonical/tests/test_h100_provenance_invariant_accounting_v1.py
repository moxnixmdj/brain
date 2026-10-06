import unittest
from canonical.runtime import h100_provenance_invariant_accounting_v1 as a
class T(unittest.TestCase):
 def test_weight_to_code_relabel_does_not_change_target_adapted_total(self):
  r=a.relabel_invariant(100,100,0)
  self.assertTrue(r["target_adapted_bytes_invariant"])
  self.assertEqual(r["before"]["target_adapted_capability_bytes"],100)
  self.assertEqual(r["after"]["target_adapted_capability_bytes"],100)
 def test_generic_code_separate(self):
  r=a.account(learned_target_bytes=10,deterministic_target_bytes=20,generic_frozen_code_bytes=1000)
  self.assertEqual(r["target_adapted_capability_bytes"],30)
  self.assertEqual(r["generic_frozen_code_bytes"],1000)
 def test_task_state_separate(self):
  r=a.account(learned_target_bytes=0,deterministic_target_bytes=5,task_state_bytes=999)
  self.assertEqual(r["target_adapted_capability_bytes"],5)
  self.assertEqual(r["task_state_bytes"],999)
 def test_invalid(self):
  with self.assertRaises(a.AccountingError): a.account(learned_target_bytes=-1,deterministic_target_bytes=0)
if __name__=="__main__": unittest.main(verbosity=2)
