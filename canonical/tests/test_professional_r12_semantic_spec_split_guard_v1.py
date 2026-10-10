import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_r12_semantic_spec_split_guard_v1 as v

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
 def test_current_candidate_enforces_split(self):
  o=v.verify(root=ROOT)
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["safe_universal_property_proved"])
  self.assertFalse(o["stronger_r12_semantic_sufficiency_proved"])
  self.assertFalse(o["authority_transport_allowed"])
 def test_safe_failure_blocks_split_pass(self):
  with patch.object(v.safev,"verify",return_value={"pass":False}):
   o=v.verify(root=ROOT);self.assertFalse(o["pass"])
 def test_safe_overclaim_is_rejected(self):
  fake={"pass":True,"safe_property_truth_proved":True,"claim_id":v.SAFE_CLAIM_ID,
        "stronger_r12_claim_id":v.STRONGER_CLAIM_ID,
        "stronger_r12_semantic_sufficiency_proved":True,"stronger_r12_authority_transported":False}
  with patch.object(v.safev,"verify",return_value=fake):
   o=v.verify(root=ROOT);self.assertFalse(o["pass"])
 def test_no_terminal_credit(self):
  o=v.verify(root=ROOT);self.assertEqual(o["terminal_credit_delta"],0);self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
