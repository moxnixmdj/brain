import unittest
from unittest.mock import patch
from canonical.runtime import professional_r12_semantic_property_repair_verify_v2 as v

class Tests(unittest.TestCase):
 def test_current_repaired_claim_proves_semantic_property(self):
  o=v.verify()
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["semantic_property_truth_authority"])
  self.assertTrue(o["claim_scoped_totality_proved"])
  self.assertTrue(o["cc_r3_terminal_closure_proved"])
  self.assertTrue(o["r4_proof_realization_authority"])
  self.assertFalse(o["predecessor_authority_transported"])
  self.assertFalse(o["terminal_authority"])
 @patch.object(v.u,"verify")
 def test_cc_r3_composition_cannot_be_skipped(self,m):
  m.return_value={"pass":False}
  o=v.verify()
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"UNIVERSAL_TOTALITY_UNPROVED")
 @patch.object(v.u.candidate,"verify")
 def test_fail_closed_unknown_is_load_bearing(self,m):
  m.return_value={"pass":True,"fail_closed_on_unknown":False}
  o=v.verify()
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"FAIL_CLOSED_UNKNOWN_UNPROVED")
 def test_credit_is_only_new_claim(self):
  o=v.verify()
  self.assertEqual(o["semantic_claim_id"],v.NEW)
  self.assertNotEqual(o["semantic_claim_id"],v.OLD)
  self.assertFalse(o["quality_authority"]);self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
