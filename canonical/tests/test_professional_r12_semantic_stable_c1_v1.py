from copy import deepcopy
from pathlib import Path
import json,unittest
from canonical.runtime import professional_r12_semantic_stable_c1_v1 as v
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as p

ROOT=Path(__file__).resolve().parents[2]

def current_inputs():
 out=p.verify(repo_root=ROOT)
 r12=next(x for x in out["claims"] if x["leaf_id"]==v.LEAF_ID)
 docs=[]
 for rel,_ in (v.FRESH_V3_RECEIPT,v.COMPOSITION_RECEIPT,v.DECOMPOSITION):
  docs.append(json.loads((ROOT/rel).read_text(encoding="utf-8")))
 return r12,*docs

class StableC1Tests(unittest.TestCase):
 def test_current_stable_c1_passes_only_c1(self):
  o=v.verify(repo_root=ROOT)
  self.assertTrue(o["pass"],o)
  self.assertEqual(o["claim_id"],v.CLAIM_ID)
  self.assertTrue(o["c1_assumption_guarantee_composition_proved"])
  self.assertFalse(o["cc_r3_terminal_closure_proved"])
  self.assertFalse(o["r4_proof_closure"])
  self.assertFalse(o["semantic_property_truth_authority"])
 def test_old_v2_claim_fails(self):
  r,a,b,c=current_inputs();r=deepcopy(r);r["frozen_claim"]["claim_id"]=v.OLD_V2_CLAIM_ID
  o=v.evaluate(r,a,b,c)
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"STABLE_CLAIM_ID_DRIFT")
 def test_composition_admissibility_false_fails(self):
  r,a,b,c=current_inputs();b=deepcopy(b);b["composition_admissible"]=False
  o=v.evaluate(r,a,b,c)
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"COMPOSITION_NOT_12_OF_12")
 def test_composed_subject_drift_fails(self):
  r,a,b,c=current_inputs();b=deepcopy(b);b["composed_subject"]["subject_sha256"]="0"*64
  o=v.evaluate(r,a,b,c)
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"COMPOSED_SUBJECT_DRIFT")
 def test_c1_decomposition_drift_fails(self):
  r,a,b,c=current_inputs();c=deepcopy(c)
  rows=c.get("clauses") or c.get("contract_clauses") or c.get("rows")
  next(x for x in rows if x.get("id")=="R12C1_ASSUMPTION_GUARANTEE_COMPOSITION")["fragment"]="something else"
  o=v.evaluate(r,a,b,c)
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"C1_DECOMPOSITION_DRIFT")
 def test_v3_current_receipt_authority_overclaim_fails(self):
  r,a,b,c=current_inputs();a=deepcopy(a);a["observed"]["semantic_property_truth_authority"]=True
  o=v.evaluate(r,a,b,c)
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"CURRENT_V3_RECEIPT_AUTHORITY_OVERCLAIM:semantic_property_truth_authority")

if __name__=="__main__":unittest.main(verbosity=2)
