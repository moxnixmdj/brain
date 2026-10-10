import unittest
from canonical.runtime import professional_v10_subject_builder_v1 as b
from canonical.runtime import professional_quality_declared_system_subject_verify_v2 as subject_verify

class Tests(unittest.TestCase):
 def test_builds_minimal_v10_successor(self):
  o=b.build();self.assertEqual(o["schema"],subject_verify.SUBJECT_SCHEMA)
  self.assertEqual(o["subject_id"],b.SUBJECT_ID)
  self.assertEqual(o["builder"]["removed_component_count"],1)
  self.assertEqual(o["builder"]["added_component_count"],2)
  paths=[x["path"] for x in o["system_material"]["components"]]
  self.assertNotIn(b.OLD_BINDER_PATH,paths)
  self.assertIn(b.NEW_BINDER_PATH,paths)
  self.assertIn(b.V2_MANIFEST_PATH,paths)
  self.assertEqual(len(paths),len(set(paths)))
 def test_semantic_authority_is_parameterized_and_zero_credit(self):
  o=b.build();a=o["dependency_closure"]["semantic_admission_authority"]
  self.assertFalse(a["claim_pack_hardcoded"]);self.assertTrue(a["exact_current_claim_required"])
  self.assertTrue(a["four_root_totality_and_r4_required"])
  self.assertFalse(o["terminal_authority"])
 def test_hash_is_deterministic(self):
  self.assertEqual(b.build()["subject_sha256"],b.build()["subject_sha256"])

if __name__=="__main__":unittest.main(verbosity=2)
