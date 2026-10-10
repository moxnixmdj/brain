from __future__ import annotations
import json,tempfile,unittest
from hashlib import sha1
from pathlib import Path
from canonical.runtime.executable_refinement_verifier_refinement_checker_v1 import verify

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"canonical/governance/EXECUTABLE_REFINEMENT_VERIFIER_ABSTRACT_SPEC_20261010_V1.json"
SUB=Path("canonical/runtime/executable_refinement_verifier_v1.py")
def spec():return json.loads(SPEC.read_text())
def blob(p):
    b=p.read_bytes();return sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def temp_subject(src):
    td=tempfile.TemporaryDirectory();r=Path(td.name);p=r/SUB;p.parent.mkdir(parents=True);p.write_text(src);return td,r

class ERVRefinementTests(unittest.TestCase):
    def test_current(self):
        o=verify(spec(),repo_root=ROOT);self.assertTrue(o["pass"],o)
        self.assertEqual(o["rejection_witness_count"],42)
        self.assertEqual(o["acceptance_witness_count"],18)
        self.assertEqual(o["witness_count"],60)
        self.assertFalse(o["refinement_verified"] is False)
        self.assertFalse(o["semantic_truth_authority"])
        self.assertFalse(o["execution_authority"])
        self.assertEqual(o["terminal_credit_delta"],0)
    def test_missing_reason_spec_rejected(self):
        s=spec();s["direct_fail_reasons"].remove("PROOF_CLASS_UNSUPPORTED")
        o=verify(s,repo_root=ROOT);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"DIRECT_FAIL_REASON_CENSUS_MISMATCH")
    def test_blob_drift_rejected(self):
        td,r=temp_subject((ROOT/SUB).read_text()+"\n")
        try:
            o=verify(spec(),repo_root=r);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"SUBJECT_BLOB_DRIFT")
        finally:td.cleanup()
    def test_allowed_constant_mutation_rejected(self):
        src=(ROOT/SUB).read_text().replace('"STUTTER"','"MAGIC_ALLOWED"',1)
        td,r=temp_subject(src)
        try:
            s=spec();s["subject"]["git_blob_sha"]=blob(r/SUB)
            o=verify(s,repo_root=r);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"CONSTANT_SURFACE_MISMATCH")
        finally:td.cleanup()
    def test_success_authority_mutation_rejected(self):
        src=(ROOT/SUB).read_text().replace('"PASS__STRUCTURAL_REFINEMENT_BINDING_VERIFIED"','"PASS__BROKEN_STRUCTURAL_BINDING"',1)
        td,r=temp_subject(src)
        try:
            s=spec();s["subject"]["git_blob_sha"]=blob(r/SUB)
            o=verify(s,repo_root=r);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"SUCCESS_PROJECTION_MISMATCH")
        finally:td.cleanup()

if __name__=="__main__":unittest.main(verbosity=2)
