from __future__ import annotations
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_root_binding_compat_v2 as c

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def test_v1_explicit_nonauthority_passes(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V4.json")
        o=c.normalize(b,repo_root=ROOT)
        self.assertTrue(o["pass"],o)
        self.assertFalse(o["legacy_v2_inheritance_used"])

    def test_exact_r3_v2_inheritance_passes(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
        v=load("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json")
        o=c.normalize(b,verification=v,repo_root=ROOT)
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["legacy_v2_inheritance_used"])
        self.assertFalse(o["global_subject_identity_authority"])

    def test_arbitrary_v2_missing_global_field_fails(self):
        b={
            "schema":c.V2,"root_id":"R99_FAKE",
            "root_subject_binding_authority":False,"terminal_authority":False,
            "subject_kind":"DECLARED_SYSTEM","subject_id":"x","subject_sha256":"a"*64,
        }
        self.assertEqual(c.normalize(b,repo_root=ROOT)["reason"],"V2_MISSING_GLOBAL_FIELD_WITHOUT_EXACT_INHERITANCE")

    def test_r3_v2_requires_current_verification(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
        self.assertEqual(c.normalize(b,repo_root=ROOT)["reason"],"R3_V2_CURRENT_VERIFICATION_REQUIRED")

    def test_r3_v2_inheritance_mismatch_fails(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
        v=load("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json")
        v["exact_blobs"]["base_v1_binding"]="0"*40
        self.assertEqual(c.normalize(b,verification=v,repo_root=ROOT)["reason"],"R3_V2_CURRENT_VERIFICATION_INHERITANCE_MISMATCH")

    def test_explicit_v2_global_authority_fails(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
        b["global_subject_identity_authority"]=True
        self.assertEqual(c.normalize(b,repo_root=ROOT)["reason"],"V2_GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")

    def test_terminal_self_authority_fails(self):
        b=load("canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json")
        b["terminal_authority"]=True
        self.assertEqual(c.normalize(b,repo_root=ROOT)["reason"],"BINDING_TERMINAL_AUTHORITY_FORBIDDEN")

if __name__=="__main__":
    unittest.main(verbosity=2)
