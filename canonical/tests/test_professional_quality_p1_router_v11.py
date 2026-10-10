from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import professional_quality_p1_router_v11 as r

def claims():
    return [{"leaf_id":f"PQ::R{i}::SEMANTIC","frozen_claim":{"claim_id":f"{i:064x}"}} for i in range(12)]

def pack():
    return {"pass":True,"semantic_claim_count":12,"unique_claim_id_count":12,"claims":claims()}

def state():
    return {
      r.V11_SUBJECT_REF_KEY:{"path":"canonical/governance/v11.json","git_blob_sha":"a"*40},
      r.SEMANTIC_BINDINGS_KEY:{f"{i:064x}":{"certificate":{"path":f"canonical/evidence/c{i}.json","git_blob_sha":"b"*40}} for i in range(12)}
    }

def positive():
    return {"final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True}

class V11Tests(unittest.TestCase):
 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r,"_cert_path")
 @patch.object(r.claim_pack,"verify")
 @patch.object(r.base,"route")
 @patch.object(r,"_v11_subject_ok")
 def test_positive_requires_all_twelve(self,sub,base,cp,path,trusted):
  sub.return_value={"pass":True};base.return_value=positive();cp.return_value=pack();path.return_value=object()
  trusted.side_effect=lambda **kw:{"pass":True,"local_material_totality_verified":True,"semantic_acceptance_bound":True,"policy_cover_result_sha256":"c"*64}
  o=r.route(state(),repo_root=".")
  self.assertTrue(o["v11_all_semantic_local_totality_verified"]);self.assertEqual(o["v11_semantic_claim_count"],12);self.assertEqual(trusted.call_count,12)

 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r,"_cert_path")
 @patch.object(r.claim_pack,"verify")
 @patch.object(r.base,"route")
 @patch.object(r,"_v11_subject_ok")
 def test_missing_claim_rejected_before_verifier(self,sub,base,cp,path,trusted):
  sub.return_value={"pass":True};base.return_value=positive();cp.return_value=pack()
  s=state();del s[r.SEMANTIC_BINDINGS_KEY][f"{0:064x}"]
  o=r.route(s,repo_root=".")
  self.assertEqual(o["reason"],"V11_SEMANTIC_CLAIM_BINDING_SET_MISMATCH");trusted.assert_not_called()

 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r,"_cert_path")
 @patch.object(r.claim_pack,"verify")
 @patch.object(r.base,"route")
 @patch.object(r,"_v11_subject_ok")
 def test_one_semantic_failure_rejects_positive(self,sub,base,cp,path,trusted):
  sub.return_value={"pass":True};base.return_value=positive();cp.return_value=pack();path.return_value=object()
  def fx(**kw):
   return {"pass":False,"local_material_totality_verified":False,"semantic_acceptance_bound":False} if kw["expected_claim_id"]==f"{7:064x}" else {"pass":True,"local_material_totality_verified":True,"semantic_acceptance_bound":True}
  trusted.side_effect=fx
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V11_SEMANTIC_LOCAL_TOTALITY_REJECTED");self.assertEqual(o["claim_id"],f"{7:064x}")

 @patch.object(r.claim_pack,"verify")
 @patch.object(r.base,"route")
 @patch.object(r,"_v11_subject_ok")
 def test_nonpositive_v10_route_cannot_become_positive(self,sub,base,cp):
  sub.return_value={"pass":True};base.return_value={"status":"ABSTAIN","positive_certification_authorized":False}
  o=r.route(state(),repo_root=".")
  self.assertFalse(o["v11_all_semantic_local_totality_verified"]);cp.assert_not_called()

 @patch.object(r.base,"route")
 @patch.object(r,"_v11_subject_ok")
 def test_subject_failure_blocks_v10(self,sub,base):
  sub.return_value={"pass":False,"reason":"bad"}
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V11_DECLARED_SYSTEM_SUBJECT_INVALID");base.assert_not_called()

if __name__=="__main__":unittest.main(verbosity=2)
