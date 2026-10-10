import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_root_binding_compat_v1 as c

ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
BASE={"root_subject_binding_authority":False,"terminal_authority":False,"subject_kind":"DECLARED_SYSTEM","subject_id":"s","subject_sha256":"a"*64}

class Tests(unittest.TestCase):
 def test_v1_explicit_nonauthority_passes(self):
  d=dict(BASE,schema=c.V1,global_subject_identity_authority=False);self.assertTrue(c.normalize(d)["pass"])
 def test_exact_r3_v2_verified_inheritance_passes(self):
  d=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
  o=c.normalize(d);self.assertTrue(o["pass"],o);self.assertTrue(o["inheritance_proved"])
 def test_arbitrary_v2_missing_global_field_fails(self):
  d=dict(BASE,schema=c.V2,root_id="R99_FAKE")
  self.assertEqual(c.normalize(d)["reason"],"V2_MISSING_GLOBAL_FIELD_WITHOUT_EXACT_INHERITANCE")
 def test_v2_explicit_global_authority_fails(self):
  d=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json");d["global_subject_identity_authority"]=True
  self.assertEqual(c.normalize(d)["reason"],"V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
 def test_v2_bad_predecessor_reference_fails(self):
  d=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json");d["supersedes"]["git_blob_sha"]="0"*40
  self.assertEqual(c.normalize(d)["reason"],"R3_V2_PREDECESSOR_REFERENCE_INVALID")
 def test_v1_guarantee_preservation_required(self):
  d=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json");d["binding_scope"]["guarantees"]=[]
  self.assertEqual(c.normalize(d)["reason"],"R3_V2_V1_GUARANTEE_PRESERVATION_MISSING")
 def test_root_self_authority_fails(self):
  d=dict(BASE,schema=c.V1,global_subject_identity_authority=False,root_subject_binding_authority=True);self.assertEqual(c.normalize(d)["reason"],"BINDING_SELF_ROOT_AUTHORITY_FORBIDDEN")
 def test_terminal_authority_fails(self):
  d=dict(BASE,schema=c.V1,global_subject_identity_authority=False,terminal_authority=True);self.assertEqual(c.normalize(d)["reason"],"BINDING_TERMINAL_AUTHORITY_FORBIDDEN")
 def test_unknown_schema_fails(self):
  d=dict(BASE,schema="V99");self.assertEqual(c.normalize(d)["reason"],"BINDING_SCHEMA_UNSUPPORTED")
if __name__=="__main__":unittest.main(verbosity=2)
