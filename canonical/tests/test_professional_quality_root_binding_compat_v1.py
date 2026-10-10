import unittest
from canonical.runtime import professional_quality_root_binding_compat_v1 as c
BASE={"root_subject_binding_authority":False,"terminal_authority":False,"subject_kind":"DECLARED_SYSTEM","subject_id":"s","subject_sha256":"a"*64}
class Tests(unittest.TestCase):
 def test_v1_explicit_nonauthority_passes(self):
  d=dict(BASE,schema=c.V1,global_subject_identity_authority=False);self.assertTrue(c.normalize(d)["pass"])
 def test_v2_legacy_absent_global_field_passes_as_nonauthority(self):
  d=dict(BASE,schema=c.V2);o=c.normalize(d);self.assertTrue(o["pass"],o);self.assertTrue(o["legacy_v2_missing_global_field_normalized"])
 def test_v2_explicit_global_authority_fails(self):
  d=dict(BASE,schema=c.V2,global_subject_identity_authority=True);self.assertEqual(c.normalize(d)["reason"],"V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
 def test_root_self_authority_fails(self):
  d=dict(BASE,schema=c.V2,root_subject_binding_authority=True);self.assertEqual(c.normalize(d)["reason"],"BINDING_SELF_ROOT_AUTHORITY_FORBIDDEN")
 def test_terminal_authority_fails(self):
  d=dict(BASE,schema=c.V1,global_subject_identity_authority=False,terminal_authority=True);self.assertEqual(c.normalize(d)["reason"],"BINDING_TERMINAL_AUTHORITY_FORBIDDEN")
 def test_unknown_schema_fails(self):
  d=dict(BASE,schema="V99");self.assertEqual(c.normalize(d)["reason"],"BINDING_SCHEMA_UNSUPPORTED")
if __name__=="__main__":unittest.main(verbosity=2)
