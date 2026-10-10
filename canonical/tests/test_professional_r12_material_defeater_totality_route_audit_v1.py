from copy import deepcopy
import json,unittest
from pathlib import Path
from canonical.runtime import professional_r12_material_defeater_totality_route_audit_v1 as v
ROOT=Path(__file__).resolve().parents[2]
def docs():
 return [json.loads((ROOT/p).read_text()) for p in (v.R12_PATH,v.CATALOG_PATH,v.ROOT_THEOREM_PATH)]
class Tests(unittest.TestCase):
 def test_current_routes_fail_closed_without_totality(self):
  o=v.verify(repo_root=ROOT);self.assertTrue(o["pass"],o)
  self.assertFalse(o["material_defeater_totality_proved"])
  self.assertFalse(o["cc_r3_terminal_closure_proved"])
  self.assertFalse(o["known_defeater_catalog_is_totality_authority"])
  self.assertFalse(o["eight_clause_reconciliation_is_totality_authority"])
 def test_catalog_must_preserve_incompleteness_boundary(self):
  r,c,t=docs();c=deepcopy(c);c["hard_nonclaims"]=[]
  o=v.evaluate_documents(r,c,t);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"CATALOG_COMPLETENESS_BOUNDARY_MISSING")
 def test_eight_clauses_cannot_be_inflated_to_cc_r3(self):
  r,c,t=docs();r=deepcopy(r);r["derived"]["cc_r3_terminal_closure_proved"]=True
  o=v.evaluate_documents(r,c,t);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"R12_CC_R3_ALREADY_OR_FALSELY_CLOSED")
 def test_unknown_must_remain_fail_closed(self):
  r,c,t=docs();t=deepcopy(t);t["hard_rules"]=[x for x in t["hard_rules"] if x!="UNKNOWN_NEVER_EQUALS_PROVED"]
  o=v.evaluate_documents(r,c,t);self.assertFalse(o["pass"]);self.assertIn("UNKNOWN_NEVER_EQUALS_PROVED",o["reason"])
 def test_new_named_category_does_not_imply_new_root(self):
  r,c,t=docs();t=deepcopy(t);t["new_e_admission"]["default"]="ADMIT"
  o=v.evaluate_documents(r,c,t);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"NEW_E_DEFAULT_DRIFT")
if __name__=="__main__":unittest.main(verbosity=2)
