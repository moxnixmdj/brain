import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v2 as v

def setup(root):
 claim=root/"claim.json";claim.write_text(json.dumps({"claim_id":v.CLAIM_ID,"claim_kind":"PROPERTY_CERTIFICATE",
  "mission_blob_sha":"m","scope_sha256":"s","target_predicate_sha256":"t","semantics_sha256":"e","epoch":"x","authority_id":"a"}))
 tc=root/"tc.json";tc.write_text("{}");tv=root/"tv.py";tv.write_text("# exact verifier fixture")
 tr=root/"tr.json";tr.write_text("{}")
 state={v.v9.base.STEP_BINDINGS_KEY:{v.v9.base.FINAL_STEP:{
  "material_totality_certificate":{"path":"canonical/governance/tc.json","git_blob_sha":"1"},
  "material_totality_semantic_verifier":{"path":v.TOTALITY_VERIFIER_PATH,"git_blob_sha":v.TOTALITY_VERIFIER_BLOB},
  "material_totality_semantic_verification":{"path":"canonical/verification/tr.json","git_blob_sha":"2"}}}
 rp=root/"state.json";rp.write_text(json.dumps(state))
 active=json.loads(claim.read_text());active["claim_id"]=v.CLAIM_ID
 cert={"schema":v.CERT_SCHEMA,"root_id":v.ROOT_ID,"claim_id":v.CLAIM_ID,
  "active_claim":{"path":v.CLAIM_PATH,"git_blob_sha":v.CLAIM_BLOB},
  "material_totality_certificate":state[v.v9.base.STEP_BINDINGS_KEY][v.v9.base.FINAL_STEP]["material_totality_certificate"],
  "material_totality_semantic_verifier":state[v.v9.base.STEP_BINDINGS_KEY][v.v9.base.FINAL_STEP]["material_totality_semantic_verifier"],
  "material_totality_semantic_verification":state[v.v9.base.STEP_BINDINGS_KEY][v.v9.base.FINAL_STEP]["material_totality_semantic_verification"],
  "v9_route_state":{"path":"canonical/evidence/state.json","git_blob_sha":"3"},
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"accounting":{"terminal_credit_delta":0}}
 cp=root/"cert.json";cp.write_text(json.dumps(cert))
 paths={v.CLAIM_PATH:claim,"canonical/governance/tc.json":tc,v.TOTALITY_VERIFIER_PATH:tv,
  "canonical/verification/tr.json":tr,"canonical/evidence/state.json":rp}
 return active,cp,cert,paths

def positive():
 return {"final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True,
  "v9_executable_r12_totality_semantics_verified":True,
  "r12_totality_semantic_verification":{"pass":True,"semantic_totality_verified":True,
   "semantic_property_claim_id":v.totality_verify.reuse.PROPERTY_CLAIM_ID}}

class Tests(unittest.TestCase):
 @patch.object(v.v9,"route")
 @patch.object(v,"_safe")
 def test_v2_positive_exact_binding(self,safe,route):
  route.return_value=positive()
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);active,cp,_,paths=setup(root);safe.side_effect=lambda _root,r,_prefixes:paths.get(r.get("path"))
   o=v.verify_certificate(root=root,certificate_path=cp,active_claim=active,root_id=v.ROOT_ID)
   self.assertTrue(o["pass"],o);self.assertTrue(o["cc_r3_terminal_closure_proved"])
 @patch.object(v.v9,"route")
 @patch.object(v,"_safe")
 def test_abstention_still_fails(self,safe,route):
  route.return_value={"final_step_outcome":"ABSTAIN","positive_certification_authorized":False}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);active,cp,_,paths=setup(root);safe.side_effect=lambda _root,r,_prefixes:paths.get(r.get("path"))
   o=v.verify_certificate(root=root,certificate_path=cp,active_claim=active,root_id=v.ROOT_ID);self.assertFalse(o["pass"])
 @patch.object(v.v9,"route")
 @patch.object(v,"_safe")
 def test_old_v1_totality_verifier_is_rejected(self,safe,route):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);active,cp,cert,paths=setup(root)
   cert["material_totality_semantic_verifier"]={"path":"canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v1.py","git_blob_sha":"x"}
   cp.write_text(json.dumps(cert));safe.side_effect=lambda _root,r,_prefixes:paths.get(r.get("path"))
   o=v.verify_certificate(root=root,certificate_path=cp,active_claim=active,root_id=v.ROOT_ID)
   self.assertFalse(o["pass"]);route.assert_not_called()

if __name__=="__main__":unittest.main(verbosity=2)
