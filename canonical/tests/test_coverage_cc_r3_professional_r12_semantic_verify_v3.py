from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v3 as v

ROOT=Path(__file__).resolve().parents[2]
ACTIVE=json.loads((ROOT/v.CLAIM_PATH).read_text())

def cert():
 return {"schema":v.CERT_SCHEMA,"root_id":v.ROOT_ID,"claim_id":v.CLAIM_ID,
  "active_claim":{"path":v.CLAIM_PATH,"git_blob_sha":v.CLAIM_BLOB},
  "r12_reconciliation":{"path":v.RECON_PATH,"git_blob_sha":v.RECON_BLOB},
  "stable_c8_verification":{"path":v.C8_PATH,"git_blob_sha":v.C8_BLOB},
  "material_totality_certificate":{"path":"canonical/governance/future-totality.json","git_blob_sha":"a"*40},
  "material_totality_semantic_verifier":{"path":v.TOTALITY_VERIFIER_PATH,"git_blob_sha":v.TOTALITY_VERIFIER_BLOB},
  "material_totality_semantic_verification":{"path":"canonical/verification/future-totality.json","git_blob_sha":"b"*40},
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"accounting":{"terminal_credit_delta":0}}

def run_doc(doc,sem_result):
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/"c.json";p.write_text(json.dumps(doc))
  with patch.object(v.sem,"validate",return_value=sem_result):
   return v.verify_certificate(root=ROOT,certificate_path=p,active_claim=ACTIVE,root_id=v.ROOT_ID)

class Tests(unittest.TestCase):
 def test_current_stable_c8_plus_totality_closes_mechanism(self):
  o=run_doc(cert(),{"pass":True,"semantic_totality_verified":True})
  self.assertTrue(o["pass"],o);self.assertTrue(o["cc_r3_terminal_closure_proved"])
  self.assertTrue(o["stable_c8_reused"]);self.assertFalse(o["new_v9_positive_route_required"])
 def test_missing_totality_still_fails(self):
  o=run_doc(cert(),{"pass":False,"semantic_totality_verified":False})
  self.assertFalse(o["pass"]);self.assertIn("EXECUTABLE_MATERIAL_TOTALITY_NOT_PROVED",o["errors"])
 def test_stable_c8_blob_drift_fails(self):
  c=cert();c["stable_c8_verification"]["git_blob_sha"]="0"*40
  o=run_doc(c,{"pass":True,"semantic_totality_verified":True})
  self.assertFalse(o["pass"]);self.assertIn("STABLE_C8_VERIFICATION_REF_MISMATCH",o["errors"])
 def test_no_new_v9_route_is_required_by_certificate(self):
  self.assertNotIn("v9_route_state",cert())
 def test_current_c8_receipt_is_real_and_independently_replayed(self):
  c8=json.loads((ROOT/v.C8_PATH).read_text())
  self.assertEqual(c8["claim_id"],v.CLAIM_ID)
  self.assertTrue(c8["reasoning"]["witness_is_real_executed_route"])
  self.assertTrue(c8["reasoning"]["witness_is_independently_replayed"])
  self.assertTrue(c8["consequence"]["r12_c8_nonvacuity_proved"])

if __name__=="__main__":unittest.main(verbosity=2)
