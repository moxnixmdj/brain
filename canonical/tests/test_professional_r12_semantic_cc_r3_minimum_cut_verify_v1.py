from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_semantic_cc_r3_minimum_cut_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
CUT=ROOT/v.CUT_PATH

def doc():
 return json.loads(CUT.read_text(encoding="utf-8"))

class R12SemanticCCR3MinimumCutVerifyV1Tests(unittest.TestCase):
 def test_current_cut_passes_and_stays_open(self):
  out=v.verify(repo_root=ROOT)
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["open_obligation_count"],3)
  self.assertEqual(tuple(out["open_obligation_ids"]),v.EXPECTED_OBLIGATIONS)
  self.assertFalse(out["cc_r3_terminal_closure"])
  self.assertFalse(out["semantic_property_truth_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)

 def test_dropping_one_obligation_fails_closed(self):
  x=doc();x["cut"].pop()
  out=v.validate(x,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"CUT_NOT_EXACT_THREE")

 def test_premature_close_fails_closed(self):
  x=doc();x["cut"][0]["current_state"]="PROVED"
  out=v.validate(x,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"OBLIGATION_PREMATURELY_CLOSED")

 def test_reopening_solved_clause_fails_closed(self):
  x=doc();x["scheduler_effect"]["do_not_reopen"].remove("R12C8_NONVACUITY")
  out=v.validate(x,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"SOLVED_SET_DRIFT")

 def test_missing_required_proof_shape_fails_closed(self):
  x=doc();x["cut"][1]["required_proof_shape"]=[]
  out=v.validate(x,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"PROOF_SHAPE_MISSING")

 def test_authority_self_grant_fails_closed(self):
  x=doc();x["authority"]["cc_r3_terminal_closure"]=True
  out=v.validate(x,repo_root=ROOT)
  self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"UNAUTHORIZED_AUTHORITY")

if __name__=="__main__":
 unittest.main(verbosity=2)
