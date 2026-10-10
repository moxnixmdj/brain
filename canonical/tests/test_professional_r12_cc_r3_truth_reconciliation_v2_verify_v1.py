from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_cc_r3_truth_reconciliation_v2_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def docs():
 x=json.loads((ROOT/v.V2).read_text());c=json.loads((ROOT/v.PINS["c3"][0]).read_text());return x,c
class Tests(unittest.TestCase):
 def test_current(self):
  o=v.verify(ROOT);self.assertTrue(o["pass"],o);self.assertEqual(o["verified_clause_count"],6);self.assertEqual(o["partial_clause_count"],2)
 def test_c1_premature_close(self):
  x,c=docs();x=deepcopy(x);next(r for r in x["clause_state"] if r["id"]=="R12C1_ASSUMPTION_GUARANTEE_COMPOSITION")["state"]="VERIFIED_EXISTING"
  o=v.validate(x,c);self.assertFalse(o["pass"])
 def test_c8_premature_close(self):
  x,c=docs();x=deepcopy(x);next(r for r in x["clause_state"] if r["id"]=="R12C8_NONVACUITY")["state"]="VERIFIED_EXISTING"
  o=v.validate(x,c);self.assertFalse(o["pass"])
 def test_stronger_totality_close_rejected(self):
  x,c=docs();x=deepcopy(x);x["stronger_target_residual"]["state"]="PROVED"
  o=v.validate(x,c);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"STRONGER_TARGET_BOUNDARY_LOST")
 def test_c3_boundary_loss_rejected(self):
  x,c=docs();c=deepcopy(c);c["hard_nonclaims"]=[z for z in c["hard_nonclaims"] if z!="NO_GLOBAL_SEMANTIC_COMPLETENESS_INSIDE_ANY_ROOT"]
  o=v.validate(x,c);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"C3_BOUNDARY_MISSING")
if __name__=="__main__":unittest.main(verbosity=2)
