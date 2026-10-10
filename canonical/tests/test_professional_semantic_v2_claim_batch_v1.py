import unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_semantic_v2_claim_batch_v1 as v
ROOT=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def test_real_v2_batch(self):
  o=v.verify(root=ROOT);self.assertTrue(o["pass"],o);self.assertEqual(o["claim_count"],12);self.assertEqual(o["scope_complete_count"],12);self.assertEqual(o["unique_claim_id_count"],12)
 def test_zero_property_truth(self):
  o=v.verify(root=ROOT);self.assertEqual(o["property_truth_count"],0);self.assertTrue(all(not r["leaf_property_truth_authority"] for r in o["rows"]))
 def test_only_semantic_leaves(self):
  o=v.verify(root=ROOT);self.assertTrue(all(x["leaf_id"].endswith("::SEMANTIC") for x in o["rows"]))
 def test_manifest_pin_fails_closed(self):
  with patch.object(v,"MANIFEST_BLOB","0"*40):self.assertFalse(v.verify(root=ROOT)["pass"])
 def test_epoch_changes_ids(self):
  a=v.verify(root=ROOT,epoch="A");b=v.verify(root=ROOT,epoch="B");self.assertNotEqual({x["claim_id"] for x in a["rows"]},{x["claim_id"] for x in b["rows"]})
if __name__=="__main__":unittest.main(verbosity=2)
