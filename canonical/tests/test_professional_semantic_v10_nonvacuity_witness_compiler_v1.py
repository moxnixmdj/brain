import unittest
from canonical.runtime import professional_semantic_v10_nonvacuity_witness_compiler_v1 as v

class Tests(unittest.TestCase):
 def test_all_12_roots_have_current_bounded_witness(self):
  o=v.verify();self.assertTrue(o["pass"],o)
  self.assertEqual(o["root_count"],12);self.assertEqual(o["nonvacuity_witness_count"],12)
  self.assertEqual(len({r["root_id"] for r in o["rows"]}),12)
  self.assertTrue(all(r["bounded_nonvacuity_only"] for r in o["rows"]))
 def test_no_property_or_terminal_credit(self):
  o=v.verify();self.assertFalse(o["whole_leaf_totality_proved"])
  self.assertFalse(o["universal_fail_closed_admission_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])
 def test_special_r6_and_r12_witnesses_are_present(self):
  o=v.verify();rows={r["root_id"]:r for r in o["rows"]}
  self.assertIn("V10",rows["R6_EVIDENCE_GROUNDING_DEPENDENCE"]["witness_status"])
  self.assertIn("18_OF_18",rows["R12_META_COMPOSITION_CLOSURE"]["witness_status"])

if __name__=="__main__":unittest.main(verbosity=2)
