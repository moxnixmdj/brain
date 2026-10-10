from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import unittest
from canonical.runtime import professional_quality_leaf_binder_v2 as b

CLAIM={
 "frozen_claim":{
  "claim_id":"c"*64,
  "scope_sha256":"s"*64,
  "target_predicate_sha256":"t"*64,
  "semantics_sha256":"m"*64,
 }
}
def receipt():
 return {
  "leaf_semantic_satisfied":True,
  "semantic_claim_id":"c"*64,
  "semantic_scope_sha256":"s"*64,
  "semantic_target_predicate_sha256":"t"*64,
  "semantic_semantics_sha256":"m"*64,
  "claim_scoped_totality_proved":True,
  "cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,
  "cc_r3_terminal_closure_proved":True,
  "r4_proof_realization_authority":True,
 }

class Tests(unittest.TestCase):
 def test_exact_four_root_totality_receipt_has_no_semantic_errors(self):
  self.assertEqual(b._semantic_receipt_errors(receipt(),CLAIM),[])
 def test_boolean_satisfied_without_totality_is_rejected(self):
  r=receipt(); r.pop("claim_scoped_totality_proved")
  self.assertIn("CLAIM_SCOPED_TOTALITY_NOT_PROVED",b._semantic_receipt_errors(r,CLAIM))
 def test_each_coverage_root_is_required(self):
  fields={
   "cc_r1_reality_containment_proved":"CC_R1_NOT_PROVED",
   "cc_r2_mission_soundness_proved":"CC_R2_NOT_PROVED",
   "cc_r3_terminal_closure_proved":"CC_R3_NOT_PROVED",
   "r4_proof_realization_authority":"R4_NOT_PROVED",
  }
  for field,error in fields.items():
   r=receipt(); r[field]=False
   self.assertIn(error,b._semantic_receipt_errors(r,CLAIM))
 def test_current_claim_identity_is_exact(self):
  for field,error in [
   ("semantic_claim_id","SEMANTIC_CLAIM_ID_MISMATCH"),
   ("semantic_scope_sha256","SEMANTIC_SCOPE_BINDING_MISMATCH"),
   ("semantic_target_predicate_sha256","SEMANTIC_TARGET_BINDING_MISMATCH"),
   ("semantic_semantics_sha256","SEMANTIC_SEMANTICS_BINDING_MISMATCH"),
  ]:
   r=receipt();r[field]="x"*64
   self.assertIn(error,b._semantic_receipt_errors(r,CLAIM))
 def test_missing_current_claim_fails(self):
  self.assertEqual(b._semantic_receipt_errors(receipt(),None),["CURRENT_SEMANTIC_CLAIM_REQUIRED"])

if __name__=="__main__":unittest.main(verbosity=2)
