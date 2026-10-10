from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v4 as v

ROOT=Path(__file__).resolve().parents[2]
ACTIVE=json.loads((ROOT/v.CLAIM_PATH).read_text())

def cert():
 return {"schema":v.CERT_SCHEMA,"root_id":v.ROOT_ID,"claim_id":v.CLAIM_ID,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"accounting":{"terminal_credit_delta":0}}

def lift():
 x={"schema":v.LIFT_SCHEMA,"property_claim_id":v.CLAIM_ID,"scope_claim_id":v.SCOPE_CLAIM_ID,
  "proof_mode":"FORMAL_UNIVERSAL_REDUCTION","whole_leaf_domain_equivalence_proved":True,
  "all_admissible_inputs_covered":True,"unknown_remainder_empty":True,"independent_verified":True,
  "content_addressed":True,"finite_single_run_extrapolation":False,"source_scope_kind":"UNIVERSAL_WHOLE_LEAF",
  "terminal_credit_delta":0}
 y={"schema":v.LIFT_VERIFY_SCHEMA,"pass":True,"independent_verified":True,
  "property_claim_id":v.CLAIM_ID,"scope_claim_id":v.SCOPE_CLAIM_ID,"lift_sha256":v._canon_sha(x),
  "finite_single_run_extrapolation_rejected":True}
 return x,y

def run_doc(doc,base_result=None):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/"c.json";p.write_text(json.dumps(doc))
  if base_result is None:return v.verify_certificate(root=ROOT,certificate_path=p,active_claim=ACTIVE,root_id=v.ROOT_ID)
  with patch.object(v.v3,"verify_certificate",return_value=base_result):
   return v.verify_certificate(root=ROOT,certificate_path=p,active_claim=ACTIVE,root_id=v.ROOT_ID)

class Tests(unittest.TestCase):
 def test_current_v3_style_certificate_without_lift_fails(self):
  o=run_doc(cert())
  self.assertFalse(o["pass"]);self.assertIn("WHOLE_LEAF_TOTALITY_LIFT_REQUIRED",o["errors"])
 def test_single_exact_run_cannot_be_lifted_by_label(self):
  c=cert();x,y=lift();x["source_scope_kind"]="EXACT_RUN";x["finite_single_run_extrapolation"]=True;y["lift_sha256"]=v._canon_sha(x)
  c["whole_leaf_totality_lift"]=x;c["whole_leaf_totality_lift_verification"]=y
  o=run_doc(c)
  self.assertFalse(o["pass"]);self.assertIn("SINGLE_RUN_EXTRAPOLATION_FORBIDDEN",o["errors"])
  self.assertIn("WHOLE_LEAF_LIFT_SOURCE_SCOPE_NOT_GLOBAL",o["errors"])
 def test_valid_lift_is_still_not_enough_if_v3_fails(self):
  c=cert();x,y=lift();c["whole_leaf_totality_lift"]=x;c["whole_leaf_totality_lift_verification"]=y
  o=run_doc(c,{"pass":False,"status":"FAIL_CLOSED","errors":["BASE_TOTALITY_OPEN"],"terminal_credit_delta":0})
  self.assertFalse(o["pass"])
 def test_valid_lift_plus_v3_pass_closes_mechanism(self):
  c=cert();x,y=lift();c["whole_leaf_totality_lift"]=x;c["whole_leaf_totality_lift_verification"]=y
  base={"pass":True,"status":"BASE","cc_r3_terminal_closure_proved":True,"terminal_credit_delta":0}
  o=run_doc(c,base)
  self.assertTrue(o["pass"],o);self.assertTrue(o["whole_leaf_totality_lift_verified"])
  self.assertTrue(o["finite_single_run_extrapolation_rejected"]);self.assertEqual(o["terminal_credit_delta"],0)
 def test_lift_digest_is_content_bound(self):
  x,y=lift();x["all_admissible_inputs_covered"]=False
  ok,errors=v._lift_ok(x,y)
  self.assertFalse(ok);self.assertIn("WHOLE_LEAF_LIFT_PREMISE_UNPROVED:all_admissible_inputs_covered",errors)
  self.assertIn("WHOLE_LEAF_LIFT_VERIFY_DIGEST_MISMATCH",errors)

if __name__=="__main__":unittest.main(verbosity=2)
