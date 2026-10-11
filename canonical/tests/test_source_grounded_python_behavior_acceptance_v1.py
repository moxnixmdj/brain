from __future__ import annotations
import pathlib,tempfile,unittest
from canonical.runtime import source_grounded_python_behavior_acceptance_v1 as a
class T(unittest.TestCase):
 def fixture(self,source):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name);c=r/"candidate";v=r/"verifiers";c.mkdir();v.mkdir();(c/"calc.py").write_text(source);return td,r
 def runa(self,r,task):
  return a.run({"task_text":task,"candidate_root":"candidate","generated_verifier_path":"verifiers/generated.py","measurement_output_path":"measurement.json","output_path":"acceptance.json","timeout_s":4},r)
 def test_return_example_accepts(self):
  td,r=self.fixture("def add(a,b):\n return a+b\n")
  with td:
   o=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");self.assertTrue(o["pass"],o);self.assertEqual(o["behavior_case_count"],1);self.assertEqual(o["semantic_residual_obligation_ids"],[])
 def test_wrong_return_falsifies(self):
  td,r=self.fixture("def add(a,b):\n return a-b\n")
  with td:self.assertFalse(self.runa(r,"Function calc:add with arguments [2,3] must return 5.")["pass"])
 def test_raise_example_accepts(self):
  td,r=self.fixture("def fail(x):\n raise ValueError('bad')\n")
  with td:self.assertTrue(self.runa(r,'Function calc:fail with arguments ["x"] must raise ValueError.')["pass"])
 def test_wrong_exception_falsifies(self):
  td,r=self.fixture("def fail(x):\n raise TypeError('bad')\n")
  with td:self.assertFalse(self.runa(r,'Function calc:fail with arguments ["x"] must raise ValueError.')["pass"])
 def test_multiple_examples_compose(self):
  td,r=self.fixture("def add(a,b):\n return a+b\ndef fail(x):\n raise ValueError('bad')\n")
  with td:
   o=self.runa(r,'Function calc:add with arguments [1,2] must return 3.\nFunction calc:fail with arguments ["x"] must raise ValueError.');self.assertTrue(o["pass"],o);self.assertEqual(o["behavior_case_count"],2)
 def test_ambiguous_prose_stays_residual(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   o=self.runa(r,"Fix the parser bug.");self.assertFalse(o["pass"]);self.assertEqual(o["status"],"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS");self.assertTrue(o["semantic_residual_obligation_ids"])
 def test_mixed_explicit_and_ambiguous_blocks(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   o=self.runa(r,"Function calc:add with arguments [2,3] must return 5.\nAlso make it elegant.");self.assertFalse(o["pass"]);self.assertEqual(o["behavior_case_count"],1);self.assertEqual(len(o["semantic_residual_obligation_ids"]),1)
 def test_invalid_json_fails_closed(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   o=self.runa(r,"Function calc:add with arguments [2,] must return 5.");self.assertFalse(o["pass"]);self.assertIn("ARGUMENTS_JSON_INVALID",str(o["errors"]))
 def test_nonbuiltin_exception_fails_closed(self):
  td,r=self.fixture("def fail(): pass\n")
  with td:
   o=self.runa(r,"Function calc:fail with arguments [] must raise MyCustomError.");self.assertFalse(o["pass"]);self.assertIn("EXCEPTION_TYPE_NOT_BUILTIN",str(o["errors"]))
 def test_candidate_change_changes_snapshot_and_verdict(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   x=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");(r/"candidate"/"calc.py").write_text("def add(a,b): return 0\n");y=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");self.assertTrue(x["pass"]);self.assertFalse(y["pass"]);self.assertNotEqual(x["candidate_snapshot_sha256"],y["candidate_snapshot_sha256"])
 def test_generated_verifier_is_source_deterministic(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   x=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");y=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");self.assertEqual(x["generated_verifier_sha256"],y["generated_verifier_sha256"]);self.assertEqual(x["behavior_model_sha256"],y["behavior_model_sha256"])
 def test_builder_claim_irrelevant(self):
  td,r=self.fixture("def add(a,b): return 0\n")
  with td:
   (r/"candidate"/"claim.json").write_text('{"behavior_examples_pass":true}')
   o=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");self.assertFalse(o["pass"])
 def test_zero_external_cognition(self):
  td,r=self.fixture("def add(a,b): return a+b\n")
  with td:
   o=self.runa(r,"Function calc:add with arguments [2,3] must return 5.");self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_general_purpose_model_runtime_dependency_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
