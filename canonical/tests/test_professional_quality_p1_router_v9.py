from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import professional_quality_p1_router_v9 as r

def state():
 return {r.base.SUBJECT_REF_KEY:{"path":"canonical/governance/v9.json","git_blob_sha":"a"*40},
  r.base.STEP_BINDINGS_KEY:{r.base.FINAL_STEP:{
   "material_totality_certificate":{"path":"canonical/governance/c.json","git_blob_sha":"b"*40},
   "material_totality_semantic_verifier":{"path":"canonical/runtime/v.py","git_blob_sha":"c"*40},
   "material_totality_semantic_verification":{"path":"canonical/verification/z.json","git_blob_sha":"d"*40}}}}

def positive():
 return {"status":"ROUTE__P1_ORDINARY","route":"P1",
  "final_step_outcome":"POSITIVE_CERTIFICATE",
  "positive_certification_authorized":True,"material_totality_proved":True}

class Tests(unittest.TestCase):
 @patch.object(r.semantic_receipt,"validate")
 @patch.object(r.base,"route")
 @patch.object(r,"_v9_subject_ok")
 def test_positive_requires_semantic_rerun(self,sub,base,sem):
  sub.return_value={"pass":True};base.return_value=positive()
  sem.return_value={"pass":True,"semantic_totality_verified":True}
  o=r.route(state(),repo_root=".")
  self.assertTrue(o["v9_executable_r12_totality_semantics_verified"])
  sem.assert_called_once()
 @patch.object(r.semantic_receipt,"validate")
 @patch.object(r.base,"route")
 @patch.object(r,"_v9_subject_ok")
 def test_fake_v8_positive_rejected_when_semantic_rerun_fails(self,sub,base,sem):
  sub.return_value={"pass":True};base.return_value=positive()
  sem.return_value={"pass":False,"status":"FAIL_CLOSED"}
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V9_EXECUTABLE_R12_TOTALITY_SEMANTICS_REJECTED")
 @patch.object(r.semantic_receipt,"validate")
 @patch.object(r.base,"route")
 @patch.object(r,"_v9_subject_ok")
 def test_abstain_does_not_gain_semantic_credit(self,sub,base,sem):
  sub.return_value={"pass":True}
  base.return_value={"status":"ABSTAIN","route":"ABSTAIN","positive_certification_authorized":False}
  o=r.route(state(),repo_root=".")
  self.assertFalse(o["v9_executable_r12_totality_semantics_verified"])
  sem.assert_not_called()
 @patch.object(r.base,"route")
 @patch.object(r,"_v9_subject_ok")
 def test_subject_must_contain_v9_components(self,sub,base):
  sub.return_value={"pass":False,"reason":"V9_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT"}
  o=r.route(state(),repo_root=".")
  self.assertEqual(o["reason"],"V9_DECLARED_SYSTEM_SUBJECT_INVALID")
  base.assert_not_called()

if __name__=="__main__":unittest.main(verbosity=2)
