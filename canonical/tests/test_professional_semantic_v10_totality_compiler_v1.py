import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_semantic_v10_totality_compiler_v1 as v
ROOT=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def test_all_12_compile(self):
  o=v.compile(root=ROOT);self.assertTrue(o["pass"],o);self.assertEqual(o["totality_verification_count"],12);self.assertEqual(o["positive_receipt_count"],12)
 def test_bounded_witness_not_promoted_as_global_scope(self):
  o=v.compile(root=ROOT);self.assertTrue(all(x["bounded_witness_global_scope_transport"] is False for x in o["totalities"]))
 def test_all_totalities_exact_and_independent(self):
  o=v.compile(root=ROOT);self.assertTrue(all(x["independent_verified"] for x in o["totalities"]));self.assertTrue(all(x["claim_scoped_totality_proved"] for x in o["totalities"]))
 def test_zero_terminal_or_quality_credit(self):
  o=v.compile(root=ROOT);self.assertFalse(o["quality_authority"]);self.assertFalse(o["terminal_authority"]);self.assertEqual(o["terminal_credit_delta"],0)
 def test_binder_pin_fails_closed(self):
  with patch.object(v,"BINDER_BLOB","0"*40): self.assertFalse(v.compile(root=ROOT)["pass"])
 def test_subject_authority_must_be_bound(self):
  with patch.object(v,"SUBJECT_BLOB","0"*40): self.assertFalse(v.compile(root=ROOT)["pass"])
if __name__=="__main__":unittest.main(verbosity=2)
