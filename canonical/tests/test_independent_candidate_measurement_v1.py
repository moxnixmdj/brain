from __future__ import annotations
import pathlib,tempfile,textwrap,unittest
from canonical.runtime import independent_candidate_measurement_v1 as m
class T(unittest.TestCase):
 def fixture(self,candidate="x=1\n",verifier=None):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name);c=r/"candidate";v=r/"verifiers";c.mkdir();v.mkdir();(c/"m.py").write_text(candidate)
  body=verifier or """import json,sys,pathlib
root=pathlib.Path(sys.argv[1])
ok=(root/"m.py").read_text().strip()=="x=1"
print("__BRAIN_MEASUREMENT__"+json.dumps({"fields":{"tests_pass":{"type":"boolean","dimension":"dimensionless","value":ok}}},sort_keys=True))
raise SystemExit(0 if ok else 1)
"""
  (v/"verify.py").write_text(textwrap.dedent(body));return td,r
 def runm(self,r,**kw):
  a={"candidate_root":"candidate","verifier_path":"verifiers/verify.py","output_path":"receipt.json","timeout_s":4};a.update(kw);return m.run(a,r)
 def test_independent_boolean_measurement_pass(self):
  td,r=self.fixture()
  with td:
   o=self.runm(r);self.assertTrue(o["pass"],o);self.assertTrue(o["fields"]["tests_pass"]["value"]);self.assertFalse(o["verifier_inside_candidate"]);self.assertEqual(o["measurement_source"],"INDEPENDENT_VERIFIER_EXECUTION_NOT_BUILDER_DECLARATION")
 def test_builder_declaration_cannot_override_measurement(self):
  td,r=self.fixture()
  with td:
   (r/"candidate"/"builder_claim.json").write_text('{"tests_pass":false}')
   o=self.runm(r);self.assertTrue(o["fields"]["tests_pass"]["value"]);self.assertEqual(o["candidate_snapshot"]["file_count"],2)
 def test_candidate_change_changes_snapshot_and_falsifies(self):
  td,r=self.fixture()
  with td:
   a=self.runm(r);(r/"candidate"/"m.py").write_text("x=2\n");b=self.runm(r);self.assertNotEqual(a["candidate_snapshot_sha256"],b["candidate_snapshot_sha256"]);self.assertFalse(b["pass"]);self.assertFalse(b["fields"]["tests_pass"]["value"])
 def test_verifier_change_changes_receipt_identity(self):
  td,r=self.fixture()
  with td:
   a=self.runm(r);p=r/"verifiers"/"verify.py";p.write_text(p.read_text()+"\n# changed\n");b=self.runm(r);self.assertNotEqual(a["verifier_sha256"],b["verifier_sha256"]);self.assertNotEqual(a["receipt_sha256"],b["receipt_sha256"])
 def test_verifier_inside_candidate_rejected(self):
  td,r=self.fixture()
  with td:
   (r/"candidate"/"verify.py").write_text((r/"verifiers"/"verify.py").read_text());o=self.runm(r,verifier_path="candidate/verify.py");self.assertFalse(o["pass"]);self.assertIn("VERIFIER_INSIDE_CANDIDATE_FORBIDDEN",str(o["errors"]))
 def test_candidate_symlink_rejected(self):
  td,r=self.fixture()
  with td:
   try:(r/"candidate"/"link").symlink_to(r/"verifiers"/"verify.py")
   except OSError:self.skipTest("symlink unsupported")
   o=self.runm(r);self.assertFalse(o["pass"]);self.assertIn("CANDIDATE_SYMLINK_FORBIDDEN",str(o["errors"]))
 def test_malformed_output_fails_closed(self):
  td,r=self.fixture(verifier='print("__BRAIN_MEASUREMENT__not-json")')
  with td:
   o=self.runm(r);self.assertFalse(o["pass"]);self.assertIn("VERIFIER_MEASUREMENT_JSON_INVALID",str(o["errors"]))
 def test_timeout_fails_closed(self):
  td,r=self.fixture(verifier="import time;time.sleep(2)")
  with td:
   o=self.runm(r,timeout_s=1);self.assertFalse(o["pass"]);self.assertIn("VERIFIER_TIMEOUT",str(o["errors"]))
 def test_deterministic_receipt(self):
  td,r=self.fixture()
  with td:
   a=self.runm(r);b=self.runm(r);self.assertEqual(a["receipt_sha256"],b["receipt_sha256"]);self.assertEqual(a["fields"],b["fields"])
 def test_zero_external_cognition(self):
  td,r=self.fixture()
  with td:
   o=self.runm(r);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_general_purpose_model_runtime_dependency_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
