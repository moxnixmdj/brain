import unittest
from canonical.runtime import professional_quality_root_receipt_compat_v1 as c

class Tests(unittest.TestCase):
 def test_no_exact_blobs_unchanged(self):
  o=c.normalize({"schema":"x"});self.assertTrue(o["pass"]);self.assertFalse(o["alias_applied"])
 def test_versioned_binding_alias_normalizes(self):
  o=c.normalize({"exact_blobs":{"base_v1_binding":"a","v2_binding":"b"}});self.assertTrue(o["pass"],o);self.assertTrue(o["alias_applied"]);self.assertEqual(o["verification"]["exact_blobs"]["binding"],"b")
 def test_direct_binding_wins_when_alias_agrees(self):
  o=c.normalize({"exact_blobs":{"binding":"b","v2_binding":"b"}});self.assertTrue(o["pass"]);self.assertFalse(o["alias_applied"])
 def test_conflicting_direct_and_alias_fails(self):
  self.assertEqual(c.normalize({"exact_blobs":{"binding":"b","v2_binding":"c"}})["reason"],"CONFLICTING_VERSIONED_BINDING_ALIAS")
 def test_ambiguous_versioned_aliases_fail(self):
  self.assertEqual(c.normalize({"exact_blobs":{"v2_binding":"b","v3_binding":"c"}})["reason"],"AMBIGUOUS_VERSIONED_BINDING_ALIASES")
 def test_input_not_mutated(self):
  d={"exact_blobs":{"v2_binding":"b"}};c.normalize(d);self.assertNotIn("binding",d["exact_blobs"])

if __name__=="__main__":unittest.main(verbosity=2)
