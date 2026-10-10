from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_r12_totality_semantic_receipt_v1 as v

B={"semantic_property_claim_id":"1"*64,"semantic_scope_claim_id":"2"*64,
   "semantic_obligation":"ALL_MATERIAL_DEFEATERS","target_scope_semantics":"EXACT_RUN_MATERIAL_DEFEATERS"}

def blob(p):
 b=Path(p).read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def rerun(ok=True):
 return {"pass":ok,"semantic_totality_verified":ok,**B,"semantic_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False}
def setup_repo(result_hash=None):
 td=tempfile.TemporaryDirectory();root=Path(td.name)
 for d in ("canonical/governance","canonical/runtime","canonical/verification"):(root/d).mkdir(parents=True)
 cert={**B,"semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
       "promotion_authority":False,"terminal_authority":False}
 cp=root/"canonical/governance/cert.json";cp.write_text(json.dumps(cert))
 vp=root/"canonical/runtime/verifier_marker.py";vp.write_text("# content-addressed verifier marker\n")
 rs=rerun(True);h=hashlib.sha256(json.dumps(rs,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 receipt={"schema":v.RECEIPT_SCHEMA,"verifier_protocol":v.PROTOCOL,"pass":True,"independent":True,
  "semantic_claim_verified":True,"proof_mode":"FORMAL_REDUCTION","verifier_result_sha256":result_hash or h,
  "terminal_credit_delta":0,"errors":[],**B,
  "certificate":{"path":"canonical/governance/cert.json","git_blob_sha":blob(cp)},
  "semantic_verifier":{"path":"canonical/runtime/verifier_marker.py","git_blob_sha":blob(vp)}}
 rp=root/"canonical/verification/receipt.json";rp.write_text(json.dumps(receipt))
 return td,root,cp,vp,rp
def call(root,cp,vp,rp):
 return v.validate(root=root,certificate_ref={"path":"canonical/governance/cert.json","git_blob_sha":blob(cp)},
  semantic_verifier_ref={"path":"canonical/runtime/verifier_marker.py","git_blob_sha":blob(vp)},
  independent_verification_ref={"path":"canonical/verification/receipt.json","git_blob_sha":blob(rp)},expected_binding=B)

class Tests(unittest.TestCase):
 @patch.object(v,"_run_verifier")
 def test_exact_rerun_and_bound_receipt_pass(self,run):
  td,root,cp,vp,rp=setup_repo();run.return_value=rerun(True)
  try:self.assertTrue(call(root,cp,vp,rp)["pass"])
  finally:td.cleanup()
 @patch.object(v,"_run_verifier")
 def test_stored_pass_cannot_override_rerun_rejection(self,run):
  td,root,cp,vp,rp=setup_repo();run.return_value=rerun(False)
  try:
   o=call(root,cp,vp,rp);self.assertFalse(o["pass"]);self.assertIn("SEMANTIC_VERIFIER_REJECTED_CERTIFICATE",o["errors"])
  finally:td.cleanup()
 @patch.object(v,"_run_verifier")
 def test_receipt_must_bind_exact_rerun_hash(self,run):
  td,root,cp,vp,rp=setup_repo("0"*64);run.return_value=rerun(True)
  try:
   o=call(root,cp,vp,rp);self.assertFalse(o["pass"]);self.assertIn("RECEIPT_RERUN_RESULT_MISMATCH",o["errors"])
  finally:td.cleanup()
 @patch.object(v,"_run_verifier")
 def test_cross_claim_certificate_rejected_before_rerun(self,run):
  td,root,cp,vp,rp=setup_repo()
  try:
   c=json.loads(cp.read_text());c["semantic_property_claim_id"]="9"*64;cp.write_text(json.dumps(c))
   rec=json.loads(rp.read_text());rec["certificate"]["git_blob_sha"]=blob(cp);rp.write_text(json.dumps(rec))
   o=call(root,cp,vp,rp);self.assertFalse(o["pass"]);self.assertIn("CERTIFICATE_BINDING_MISMATCH:semantic_property_claim_id",o["errors"]);run.assert_not_called()
  finally:td.cleanup()
 @patch.object(v,"_run_verifier")
 def test_verifier_blob_drift_rejected_before_rerun(self,run):
  td,root,cp,vp,rp=setup_repo();old=blob(vp);vp.write_text("# drift\n")
  try:
   o=v.validate(root=root,certificate_ref={"path":"canonical/governance/cert.json","git_blob_sha":blob(cp)},
    semantic_verifier_ref={"path":"canonical/runtime/verifier_marker.py","git_blob_sha":old},
    independent_verification_ref={"path":"canonical/verification/receipt.json","git_blob_sha":blob(rp)},expected_binding=B)
   self.assertFalse(o["pass"]);run.assert_not_called()
  finally:td.cleanup()
if __name__=="__main__":unittest.main(verbosity=2)
