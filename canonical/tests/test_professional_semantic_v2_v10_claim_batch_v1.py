import unittest
from canonical.runtime import professional_semantic_v2_v10_claim_batch_v1 as b

class Tests(unittest.TestCase):
 def test_all_12_rebind_to_exact_v10(self):
  o=b.verify(); self.assertTrue(o["pass"],o)
  self.assertEqual(o["claim_count"],12); self.assertEqual(o["scope_complete_count"],12)
  self.assertEqual(o["unique_claim_id_count"],12)
  self.assertEqual(o["subject_id"],b.domain.SUBJECT_ID)
  self.assertEqual(o["subject_sha256"],b.domain.SUBJECT_SHA256)
 def test_every_scope_is_whole_domain_no_filters(self):
  o=b.verify()
  for row in o["rows"]:
   cs=row["claim_scope"]; d=cs["scope_definition"]["domain_definition"]
   self.assertTrue(cs["scope_definition"]["entire_admissible_leaf_domain"])
   self.assertEqual(d["filters"],[]); self.assertEqual(d["exclusions"],[])
   self.assertEqual(d["subject_id"],b.domain.SUBJECT_ID)
   self.assertEqual(d["subject_sha256"],b.domain.SUBJECT_SHA256)
 def test_no_property_credit_from_rebind(self):
  o=b.verify(); self.assertEqual(o["property_truth_count"],0)
  self.assertFalse(o["semantic_truth_authority"]); self.assertFalse(o["terminal_authority"])
  self.assertTrue(all(r["leaf_property_truth_authority"] is False for r in o["rows"]))
 def test_claim_ids_change_with_subject_epoch(self):
  a=b.verify(); z=b.verify(epoch="DIFFERENT_EPOCH")
  self.assertNotEqual({x["claim_id"] for x in a["rows"]},{x["claim_id"] for x in z["rows"]})

if __name__=="__main__":unittest.main(verbosity=2)
