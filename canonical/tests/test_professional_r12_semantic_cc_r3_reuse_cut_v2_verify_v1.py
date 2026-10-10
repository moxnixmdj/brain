from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_semantic_cc_r3_reuse_cut_v2_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
 cut=json.loads((ROOT/v.CUT).read_text())
 v1=json.loads((ROOT/v.PINS["v1_verify"][0]).read_text())
 c5=json.loads((ROOT/v.PINS["c5_verify"][0]).read_text())
 return cut,v1,c5

class R12ReuseCutV2Tests(unittest.TestCase):
 def test_current_v2(self):
  out=v.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["proved_by_reuse_count"],3)
  self.assertEqual(out["open_root_contract_clause_count"],5)
  self.assertTrue(out["stronger_material_defeater_obligation_open"])
  self.assertFalse(out["cc_r3_terminal_closure_proved"])

 def test_c8_promotion_rejected(self):
  cut,v1,c5=docs();cut=deepcopy(cut)
  next(x for x in cut["clause_reuse"] if x["id"]=="R12C8_NONVACUITY")["state"]="PROVED_BY_REUSE"
  out=v.validate(cut,v1,c5)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"CUT_PROVED_SET_OVER_OR_UNDERCLAIM")

 def test_c5_reopen_rejected(self):
  cut,v1,c5=docs();cut=deepcopy(cut)
  next(x for x in cut["clause_reuse"] if x["id"]=="R12C5_COVERAGE_ACCOUNTING")["state"]="OPEN"
  out=v.validate(cut,v1,c5)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"CUT_PROVED_SET_OVER_OR_UNDERCLAIM")

 def test_stronger_totality_promotion_rejected(self):
  cut,v1,c5=docs();cut=deepcopy(cut)
  cut["stronger_target_predicate_residual"]["state"]="PROVED"
  cut["stronger_target_predicate_residual"]["unknown_defeater_completeness_proved"]=True
  out=v.validate(cut,v1,c5)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"STRONGER_TARGET_RESIDUAL_OVERCLAIM")

 def test_count_corruption_rejected(self):
  cut,v1,c5=docs();cut=deepcopy(cut);cut["derived"]["proved_by_reuse_count"]=4
  out=v.validate(cut,v1,c5)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"DERIVED_COUNTS_INVALID")

if __name__=="__main__":
 unittest.main(verbosity=2)
