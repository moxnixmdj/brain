import unittest
from unittest.mock import patch
from canonical.runtime import professional_r12_semantic_property_repair_verify_v1 as v

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
 def test_universal_totality_cannot_be_skipped(self,m):
  m.return_value={"pass":False}
  o=v.verify()
  self.assertFalse(o["pass"])
  self.assertEqual(o["reason"],"UNIVERSAL_TOTALITY_UNPROVED")
  self.assertFalse(o["semantic_property_truth_authority"])

 @patch.object(v.u,"verify")
 def test_unknowns_must_fail_closed(self,m):
  m.return_value={"pass":True,"material_defeater_totality_proved":True,
   "cc_r3_terminal_closure_proved":True,"stable_c8_nonvacuity_proved":True,
   "generator_closure":{"fail_closed_on_unknown":False}}
  o=v.verify()
  self.assertFalse(o["pass"])
  self.assertEqual(o["reason"],"FAIL_CLOSED_UNKNOWN_UNPROVED")

 def test_property_credit_is_claim_scoped_only(self):
  o=v.verify()
  self.assertEqual(o["semantic_claim_id"],v.NEW)
  self.assertNotEqual(o["semantic_claim_id"],v.OLD)
  self.assertFalse(o["quality_authority"])
  self.assertFalse(o["acceptance_authority"])
  self.assertFalse(o["promotion_authority"])
  self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
