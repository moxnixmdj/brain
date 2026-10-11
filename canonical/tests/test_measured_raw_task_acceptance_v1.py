from __future__ import annotations
import pathlib,tempfile,textwrap,unittest
from canonical.runtime import measured_raw_task_acceptance_v1 as a
class T(unittest.TestCase):
 def fixture(self,candidate="x=1\n",fields=None):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name);c=r/"candidate";v=r/"verifiers";c.mkdir();v.mkdir();(c/"m.py").write_text(candidate)
  fields=fields or {"tests_pass":{"type":"boolean","dimension":"dimensionless","value":True}}
  code="import json,sys,pathlib\nroot=pathlib.Path(sys.argv[1])\nfields="+repr(fields)+"\nprint('__BRAIN_MEASUREMENT__'+json.dumps({'fields':fields},sort_keys=True))\n"
  (v/"verify.py").write_text(code);return td,r
 def runa(self,r,task="tests_pass must be true.",schema=None,**extra):
  schema=schema or {"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  x={"task_text":task,"candidate_root":"candidate","verifier_path":"verifiers/verify.py","candidate_field_schema":schema,"measurement_output_path":"measurement.json","output_path":"acceptance.json","timeout_s":4};x.update(extra);return a.evaluate(x,r)
 def test_measured_boolean_accepts(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r);self.assertTrue(o["pass"],o);self.assertTrue(o["candidate_accepted"]);self.assertTrue(o["acceptance_stop_authorized"]);self.assertFalse(o["direct_builder_field_input_authorized"])
 def test_false_measurement_rejects(self):
  td,r=self.fixture(fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":False}})
  with td:
   o=self.runa(r);self.assertFalse(o["pass"]);self.assertFalse(o["acceptance_stop_authorized"])
 def test_builder_claim_cannot_override_false_measurement(self):
  td,r=self.fixture(fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":False}})
  with td:
   (r/"candidate"/"builder_claim.json").write_text('{"tests_pass":true}')
   o=self.runa(r);self.assertFalse(o["pass"]);self.assertEqual(o["measured_field_ids"],["tests_pass"])
 def test_schema_mismatch_fails_closed(self):
  td,r=self.fixture(fields={"tests_pass":{"type":"enum","dimension":"dimensionless","value":"yes"}})
  with td:
   o=self.runa(r);self.assertFalse(o["pass"]);self.assertIn("MEASUREMENT_FIELD_SCHEMA_MISMATCH",str(o["errors"]))
 def test_extra_measurement_field_fails_closed(self):
  fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":True},"invented":{"type":"boolean","dimension":"dimensionless","value":True}}
  td,r=self.fixture(fields=fields)
  with td:
   o=self.runa(r);self.assertFalse(o["pass"]);self.assertIn("MEASUREMENT_FIELD_SET_MISMATCH",str(o["errors"]))
 def test_semantic_residual_still_blocks(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r,task="tests_pass must be true.\nFix the parser bug.");self.assertFalse(o["pass"]);self.assertEqual(o["acceptance_result"]["status"],"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS");self.assertTrue(o["semantic_residual_obligation_ids"])
 def test_two_independently_measured_fields_compose(self):
  fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":True},"score":{"type":"number","dimension":"points","value":6}}
  schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"},"score":{"type":"number","dimension":"points"}}
  td,r=self.fixture(fields=fields)
  with td:
   o=self.runa(r,task="tests_pass must be true.\nscore must be at least 5.",schema=schema);self.assertTrue(o["pass"],o);self.assertEqual(o["measured_field_ids"],["score","tests_pass"])
 def test_receipt_binds_candidate_and_verifier(self):
  td,r=self.fixture()
  with td:
   x=self.runa(r);(r/"candidate"/"m.py").write_text("x=2\n");y=self.runa(r);self.assertNotEqual(x["candidate_snapshot_sha256"],y["candidate_snapshot_sha256"]);self.assertEqual(x["verifier_sha256"],y["verifier_sha256"])
 def test_deterministic(self):
  td,r=self.fixture()
  with td:
   x=self.runa(r);y=self.runa(r);self.assertEqual(x["measurement_receipt_sha256"],y["measurement_receipt_sha256"]);self.assertEqual(x["acceptance_result"],y["acceptance_result"])
 def test_zero_external_cognition(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_general_purpose_model_runtime_dependency_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
