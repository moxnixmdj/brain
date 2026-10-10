import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_r12_cc_r3_semantic_binding_guard_v1 as v
ROOT=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def test_current_bytes_reject_authority_transport(self):
  o=v.verify(repo_root=ROOT); self.assertTrue(o["pass"],o)
  self.assertTrue(o["universal_positive_gate_safety_retained"])
  self.assertFalse(o["cc_r3_set_inclusion_proved"])
  self.assertFalse(o["authority_transport_allowed"])
  self.assertFalse(o["r4_proof_closure_authorized"])
 def test_countermodel_separates_safety_from_acceptance(self):
  o=v.verify(repo_root=ROOT); c=o["countermodel_to_safety_implies_full_acceptance"]
  self.assertTrue(c["safety_obligation_satisfied"]); self.assertFalse(c["full_acceptance_satisfied"])
 def test_pin_failure_fails_closed(self):
  with patch.object(v,"UNIVERSAL_BLOB","0"*40):
   o=v.verify(repo_root=ROOT); self.assertFalse(o["pass"])
 def test_zero_credit(self):
  o=v.verify(repo_root=ROOT); self.assertEqual(o["terminal_credit_delta"],0); self.assertFalse(o["semantic_property_truth_authority"])
if __name__=="__main__":unittest.main(verbosity=2)
