from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_cc_r3_truth_reconciliation_v3_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
 out={}
 for k,(rel,_) in v.PINS.items():
  out[k]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 out["v3"]=json.loads((ROOT/v.V3_PATH).read_text(encoding="utf-8"))
 return out

class Tests(unittest.TestCase):
 def test_current_truth_is_eight_clauses_but_not_cc_r3(self):
  o=v.verify(repo_root=ROOT)
  self.assertTrue(o["pass"],o)
  self.assertEqual(o["verified_clause_count"],8)
  self.assertEqual(o["partial_clause_count"],0)
  self.assertTrue(o["all_eight_root_contract_clauses_verified"])
  self.assertFalse(o["stronger_material_defeater_totality_proved"])
  self.assertFalse(o["cc_r3_terminal_closure_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])

 def test_c1_must_be_independently_proved(self):
  d=docs();d["c1"]=deepcopy(d["c1"]);d["c1"]["c1_assumption_guarantee_composition_proved"]=False
  o=v.validate(d["v3"],d["v2"],d["v2_verify"],d["c1"],d["c8"])
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"C1_NOT_PROVED")

 def test_c8_must_have_real_positive_route(self):
  d=docs();d["c8"]=deepcopy(d["c8"]);d["c8"]["truth"]["independently_observed_positive_route_count"]=0
  o=v.validate(d["v3"],d["v2"],d["v2_verify"],d["c1"],d["c8"])
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"C8_POSITIVE_ROUTE_MISSING")

 def test_stronger_totality_cannot_be_silently_closed(self):
  d=docs();d["v3"]=deepcopy(d["v3"]);d["v3"]["derived"]["stronger_target_residual_open"]=False
  o=v.validate(d["v3"],d["v2"],d["v2_verify"],d["c1"],d["c8"])
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"V3_STRONGER_TARGET_RESIDUAL_MUST_REMAIN_OPEN")

 def test_cc_r3_cannot_be_inflated_from_eight_clauses(self):
  d=docs();d["v3"]=deepcopy(d["v3"]);d["v3"]["cc_r3_terminal_closure_proved"]=True
  o=v.validate(d["v3"],d["v2"],d["v2_verify"],d["c1"],d["c8"])
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"V3_AUTHORITY_OVERCLAIM:cc_r3_terminal_closure_proved")

 def test_clause_regression_fails(self):
  d=docs();d["v3"]=deepcopy(d["v3"]);d["v3"]["clause_state"][0]["state"]="PARTIAL_EXISTING_EVIDENCE"
  o=v.validate(d["v3"],d["v2"],d["v2_verify"],d["c1"],d["c8"])
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"V3_NOT_ALL_CLAUSES_VERIFIED")

if __name__=="__main__":unittest.main(verbosity=2)
