import unittest
from canonical.runtime import professional_v8_to_v9_r12_positive_refinement_v1 as v

class Tests(unittest.TestCase):
 def test_current_exact_bytes_prove_strict_positive_refinement(self):
  o=v.verify()
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["positive_route_refinement_proved"])
  self.assertTrue(o["preserved_clause_reverification_admissible"])
  self.assertFalse(o["c8_nonvacuity_transport_proved"])
  self.assertFalse(o["cross_subject_property_authority_transport"])
 def test_v9_wraps_exact_v8(self):
  self.assertIs(v.v9.base,v.v8)
 def test_v9_uses_exact_semantic_authority(self):
  self.assertIs(v.v9.semantic_receipt,v.sem)
 def test_c8_is_not_preserved(self):
  self.assertNotIn(v.NONTRANSPORTED_CLAUSE,v.PRESERVED_CLAUSES)
  self.assertEqual(len(v.PRESERVED_CLAUSES),7)
 def test_v9_subject_is_exact_two_component_strict_extension(self):
  o=v.verify()
  self.assertEqual(o["v9_subject_strictly_extends_v8_subject_by_exact_component_count"],2)
 def test_no_property_or_terminal_authority(self):
  o=v.verify()
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
