from __future__ import annotations
import json,pathlib,tempfile,unittest
from canonical.runtime import composed_raw_software_acceptance_v1 as a
class T(unittest.TestCase):
 def fixture(self,source="def add(a,b): return a+b\n",fields=None):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name);c=r/"candidate";v=r/"verifiers";c.mkdir();v.mkdir();(c/"calc.py").write_text(source)
  fields=fields or {"tests_pass":{"type":"boolean","dimension":"dimensionless","value":True}}
  (v/"objective.py").write_text("import json,sys\nfields="+repr(fields)+"\nprint('__BRAIN_MEASUREMENT__'+json.dumps({'fields':fields},sort_keys=True))\nraise SystemExit(0 if all(x['value'] for x in fields.values() if x['type']=='boolean') else 1)\n")
  return td,r
 def runa(self,r,task,schema=None,**extra):
  x={"task_text":task,"candidate_root":"candidate","candidate_field_schema":schema or {},"objective_verifier_path":"verifiers/objective.py","objective_measurement_output_path":"obj.json","behavior_verifier_output_path":"verifiers/behavior.py","behavior_measurement_output_path":"beh.json","output_path":"accept.json","timeout_s":4};x.update(extra);return a.run(x,r)
 def test_mixed_formal_response_and_behavior(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r,'Respond with exactly "YES".\nFunction calc:add with arguments [2,3] must return 5.',response_text="YES");self.assertTrue(o["pass"],o);self.assertEqual(o["required_obligation_count"],2)
 def test_mixed_measured_field_and_behavior(self):
  td,r=self.fixture()
  schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  with td:
   o=self.runa(r,"tests_pass must be true.\nFunction calc:add with arguments [2,3] must return 5.",schema=schema);self.assertTrue(o["pass"],o);self.assertEqual(o["covered_obligation_count"],2);self.assertIsNotNone(o["candidate_snapshot_sha256"])
 def test_false_independent_field_blocks(self):
  td,r=self.fixture(fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":False}})
  schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  with td:
   o=self.runa(r,"tests_pass must be true.\nFunction calc:add with arguments [2,3] must return 5.",schema=schema);self.assertFalse(o["pass"])
 def test_wrong_behavior_blocks(self):
  td,r=self.fixture(source="def add(a,b): return 0\n")
  with td:
   o=self.runa(r,'Respond with exactly "YES".\nFunction calc:add with arguments [2,3] must return 5.',response_text="YES");self.assertFalse(o["pass"])
 def test_unsupported_prose_blocks_before_acceptance(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r,'Respond with exactly "YES".\nFix all hidden bugs.',response_text="YES");self.assertFalse(o["pass"]);self.assertEqual(o["status"],"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS");self.assertEqual(len(o["semantic_residual_obligation_ids"]),1)
 def test_builder_claim_cannot_override_independent_field(self):
  td,r=self.fixture(fields={"tests_pass":{"type":"boolean","dimension":"dimensionless","value":False}})
  schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  with td:
   (r/"candidate"/"claim.json").write_text('{"tests_pass":true}');o=self.runa(r,"tests_pass must be true.",schema=schema);self.assertFalse(o["pass"]);self.assertFalse(o["direct_builder_field_input_authorized"])
 def test_missing_objective_verifier_fails_closed(self):
  td,r=self.fixture();schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  with td:
   o=self.runa(r,"tests_pass must be true.",schema=schema,objective_verifier_path=None);self.assertFalse(o["pass"]);self.assertIn("OBJECTIVE_VERIFIER_PATH_REQUIRED",str(o["errors"]))
 def test_all_obligations_accounted(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r,'Respond with exactly "YES".\nFunction calc:add with arguments [2,3] must return 5.',response_text="YES");self.assertTrue(o["all_raw_obligations_accounted_for"]);self.assertEqual(o["required_obligation_count"],o["evaluated_obligation_count"])
 def test_measurements_bind_same_candidate_snapshot(self):
  td,r=self.fixture();schema={"tests_pass":{"type":"boolean","dimension":"dimensionless"}}
  with td:
   o=self.runa(r,"tests_pass must be true.\nFunction calc:add with arguments [2,3] must return 5.",schema=schema);self.assertTrue(o["pass"]);self.assertEqual(o["candidate_snapshot_sha256"],o["objective_measurement_receipt"]["candidate_snapshot_sha256"]);self.assertEqual(o["candidate_snapshot_sha256"],o["behavior_measurement"]["measurement_receipt"]["candidate_snapshot_sha256"])
 def test_deterministic_verdict(self):
  td,r=self.fixture()
  with td:
   x=self.runa(r,'Respond with exactly "YES".\nFunction calc:add with arguments [2,3] must return 5.',response_text="YES");y=self.runa(r,'Respond with exactly "YES".\nFunction calc:add with arguments [2,3] must return 5.',response_text="YES");self.assertEqual(x["obligation_results"],y["obligation_results"]);self.assertEqual(x["task_contract_sha256"],y["task_contract_sha256"])
 def test_zero_external_cognition(self):
  td,r=self.fixture()
  with td:
   o=self.runa(r,'Function calc:add with arguments [2,3] must return 5.');self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_general_purpose_model_runtime_dependency_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
