import unittest
from canonical.runtime import professional_v8_to_v9_r12_positive_refinement_v1 as v

class Tests(unittest.TestCase):
 def test_current_exact_v9_refines_v8(self):
  o=v.verify()
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["positive_route_refinement_proved"])
  self.assertTrue(o["preserved_clause_reverification_admissible"])
  self.assertEqual(len(o["preserved_clause_ids"]),7)
  self.assertFalse(o["c8_nonvacuity_transport_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])
 def test_v9_wraps_exact_v8_module(self):
  self.assertIs(v.v9.base,v.v8)
 def test_c8_not_preserved(self):
  self.assertNotIn("R12C8_NONVACUITY",v.PRESERVED)

if __name__=="__main__":unittest.main(verbosity=2)
