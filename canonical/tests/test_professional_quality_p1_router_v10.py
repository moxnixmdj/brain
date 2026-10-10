from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import professional_quality_p1_router_v10 as r

def state(verifier_blob=r.TRUSTED_VERIFIER_BLOB):
 return {
  r.base.base.SUBJECT_REF_KEY:{"path":"canonical/governance/v10.json","git_blob_sha":"a"*40},
  r.base.base.STEP_BINDINGS_KEY:{r.base.base.FINAL_STEP:{
   "material_totality_certificate":{"path":"canonical/evidence/c.json","git_blob_sha":"b"*40},
   "material_totality_semantic_verifier":{"path":r.TRUSTED_VERIFIER_PATH,"git_blob_sha":verifier_blob}
  }}
 }

def positive():
 return {"status":"ROUTE__P1_ORDINARY","route":"P1","final_step_outcome":"POSITIVE_CERTIFICATE",
  "positive_certification_authorized":True,"v9_executable_r12_totality_semantics_verified":True}

class Tests(unittest.TestCase):
 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r,"_safe_cert")
 @patch.object(r.base,"route")
 @patch.object(r,"_v10_subject_ok")
 def test_positive_requires_exact_trusted_verifier(self,sub,base,safe,trusted):
  sub.return_value={"pass":True};base.return_value=positive();safe.return_value=object()
  trusted.return_value={"pass":True,"local_material_totality_verified":True}
  o=r.route(state(),repo_root=".")
  self.assertTrue(o["v10_trusted_local_totality_verified"]);trusted.assert_called_once()

 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r.base,"route")
 @patch.object(r,"_v10_subject_ok")
 def test_arbitrary_verifier_rejected(self,sub,base,trusted):
  sub.return_value={"pass":True};base.return_value=positive()
  o=r.route(state("c"*40),repo_root=".")
  self.assertEqual(o["reason"],"V10_UNTRUSTED_SEMANTIC_VERIFIER_REJECTED");trusted.assert_not_called()

 @patch.object(r.trusted,"verify_certificate")
 @patch.object(r,"_safe_cert")
 @patch.object(r.base,"route")
 @patch.object(r,"_v10_subject_ok")
 def test_trusted_verifier_failure_rejects_positive(self,sub,base,safe,trusted):
  sub.return_value={"pass":True};base.return_value=positive();safe.return_value=object()
  trusted.return_value={"pass":False,"local_material_totality_verified":False}
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V10_TRUSTED_LOCAL_TOTALITY_REJECTED")

 @patch.object(r.base,"route")
 @patch.object(r,"_v10_subject_ok")
 def test_abstain_needs_no_local_totality(self,sub,base):
  sub.return_value={"pass":True};base.return_value={"status":"ABSTAIN","positive_certification_authorized":False}
  o=r.route(state(),repo_root=".")
  self.assertFalse(o["v10_trusted_local_totality_verified"])

 @patch.object(r.base,"route")
 @patch.object(r,"_v10_subject_ok")
 def test_subject_failure_prevents_base_execution(self,sub,base):
  sub.return_value={"pass":False,"reason":"V10_TRUSTED_VERIFIER_SUBJECT_PIN_MISMATCH"}
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V10_DECLARED_SYSTEM_SUBJECT_INVALID");base.assert_not_called()

if __name__=="__main__": unittest.main(verbosity=2)
