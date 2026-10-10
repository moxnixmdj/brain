import unittest
from unittest.mock import patch
from pathlib import Path
from canonical.runtime import professional_v7_to_v8_r12_positive_refinement_v1 as v

class Tests(unittest.TestCase):
    def test_current_exact_bytes_pass_and_c8_stays_open(self):
        o=v.verify()
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["positive_route_refinement_proved"])
        self.assertTrue(o["preserved_clause_reverification_admissible"])
        self.assertFalse(o["c8_nonvacuity_transport_proved"])
        self.assertFalse(o["cross_subject_property_authority_transport"])
        self.assertFalse(o["semantic_property_truth_authority"])
    def test_c8_is_never_listed_as_preserved(self):
        self.assertNotIn(v.NONTRANSPORTED_CLAUSE,v.PRESERVED_CLAUSES)
        self.assertEqual(len(v.PRESERVED_CLAUSES),7)
    def test_v8_final_step_matches_v7_final_step(self):
        self.assertEqual(v.v8.FINAL_STEP,v.v7.AUTHENTICATED_STEPS[-1])
    def test_v2_wraps_v1(self):
        self.assertIs(v.a2.base,v.a1)
    def test_cross_subject_authority_is_zero(self):
        o=v.verify()
        self.assertFalse(o["cross_subject_property_authority_transport"])
        self.assertFalse(o["quality_authority"])
        self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
