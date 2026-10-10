import unittest
from canonical.runtime import professional_semantic_v10_property_truth_compiler_v1 as v

class Tests(unittest.TestCase):
 def test_all_12_semantic_leaves_close_through_real_binder_admission(self):
  o=v.verify();self.assertTrue(o["pass"],o)
  self.assertEqual(o["verified_semantic_leaf_count"],12)
  self.assertEqual(o["open_semantic_leaf_count"],0)
  self.assertEqual(len({r["claim_id"] for r in o["rows"]}),12)
  self.assertTrue(all(r["positive_semantic_admission_authorized"] for r in o["rows"]))
  self.assertTrue(all(r["positive_route_nonvacuity_proved"] for r in o["rows"]))
  self.assertTrue(all(r["leaf_property_truth_authority"] for r in o["rows"]))
 def test_combined_property_truth_is_24_of_24_only(self):
  o=v.verify();self.assertTrue(o["semantic_property_truth_authority"])
  self.assertEqual(o["combined_professional_property_truth_count"],24)
  self.assertEqual(o["combined_professional_property_truth_total"],24)
  self.assertFalse(o["quality_authority"]);self.assertFalse(o["acceptance_authority"])
  self.assertFalse(o["promotion_authority"]);self.assertFalse(o["terminal_authority"])
 def test_each_receipt_is_content_addressed_to_distinct_basis(self):
  o=v.verify()
  self.assertEqual(len({r["basis_git_blob_sha"] for r in o["rows"]}),12)
  self.assertEqual(len({r["receipt_sha256"] for r in o["rows"]}),12)

if __name__=="__main__":unittest.main(verbosity=2)
