from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_semantic_cc_r3_clause_reuse_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
def base():
 c=load(v.CLASS);d=load(v.DECOMP);e={}
 for k,(p,h) in v.PINS.items():
  if k!="decomposition":e[k]=load(p)
 return c,d,e
class T(unittest.TestCase):
 def test_current_reuse_cut_passes_without_cc_r3_credit(self):
  o=v.evaluate();self.assertTrue(o["pass"],o);self.assertEqual(o["root_contract_reuse_supported_count"],8)
  self.assertFalse(o["known_defeater_universe_complete"]);self.assertFalse(o["cc_r3_terminal_closure"])
 def test_known_80_cannot_be_relabelled_universe_complete(self):
  c,d,e=base();c["key_truths"]["known_defeater_universe_complete"]=True
  self.assertIn("DEFEATER_COMPLETENESS_TRUTH_DRIFT",v.evaluate_documents(c,d,e)["errors"])
 def test_unknown_completeness_nonclaim_is_load_bearing(self):
  c,d,e=base();e["known_defeaters"]["hard_nonclaims"]=[]
  self.assertIn("KNOWN_DEFEATER_UNIVERSE_OVERCLAIM",v.evaluate_documents(c,d,e)["errors"])
 def test_execution_positive_cases_cannot_be_semantic_certificate(self):
  c,d,e=base();c["key_truths"]["semantic_positive_certificate_count"]=2
  self.assertIn("SEMANTIC_POSITIVE_CERTIFICATE_OVERCLAIM",v.evaluate_documents(c,d,e)["errors"])
 def test_missing_clause_breaks_reuse_cut(self):
  c,d,e=base();c["clause_rows"]=c["clause_rows"][:-1]
  self.assertIn("CLASSIFICATION_CLAUSE_COUNT_DRIFT",v.evaluate_documents(c,d,e)["errors"])
 def test_target_cannot_self_close_cc_r3(self):
  c,d,e=base();c["stronger_target_predicate"]["cc_r3_terminal_closure_proved"]=True
  self.assertIn("TARGET_PREMATURE_CLOSURE",v.evaluate_documents(c,d,e)["errors"])
 def test_new_primitive_cannot_be_claimed_without_proof(self):
  c,d,e=base();c["new_primitive_required"]=True
  self.assertIn("UNPROVED_NEW_PRIMITIVE_CLAIM",v.evaluate_documents(c,d,e)["errors"])
if __name__=="__main__":unittest.main(verbosity=2)
