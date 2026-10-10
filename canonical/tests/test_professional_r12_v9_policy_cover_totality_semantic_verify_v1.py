from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v1 as v
from canonical.runtime import professional_v9_r12_reuse_closure_v1 as reuse

SOURCE_ROOT=Path(__file__).resolve().parents[2]

def write(root:Path,rel:str,obj)->dict:
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 return {"path":rel,"git_blob_sha":v._blob(p)}

def auth(**extra):
 return {"independent_verified":True,"exact_byte_bound":True,"conclusion":"success",**extra}

def cover():
 sid="stable-r12-fixture"
 return {"state_id":sid,"worlds":[{"world_id":"w0"},{"world_id":"w1"}],
  "world_set_completeness_receipt":auth(policy_relevant_world_set_complete=True,state_id=sid),
  "policies":[{"policy_id":"p","adequate_world_ids":["w0","w1"],"cost_units":1,
   "adequacy_receipt":auth(policy_id="p",policy_adequate_on_every_listed_world=True,
    policy_safe_on_every_listed_world=True,hard_constraint_scope_complete=True,
    brain_owned=True,deployed_exact=True,resource_bound_proved=True)}],"discriminators":[]}

def problem():
 return {"semantic_property_claim_id":reuse.PROPERTY_CLAIM_ID,"semantic_scope_claim_id":reuse.SCOPE_CLAIM_ID,
  "semantic_obligation":reuse.OBLIGATION,"target_scope_semantics":reuse.TARGET_SCOPE_SEMANTICS,
  "v9_subject_id":reuse.V9_SUBJECT_ID,"v9_subject_sha256":reuse.V9_SUBJECT_SHA256,
  "real_exact_run":True,"content_addressed":True,"policy_cover_problem":cover()}

def independent(p):
 return {"pass":True,"independent_verified":True,"independent_verifier_id":"fixture-independent",
  "problem_sha256":reuse._digest(p),"semantic_property_claim_id":reuse.PROPERTY_CLAIM_ID,
  "semantic_scope_claim_id":reuse.SCOPE_CLAIM_ID,"semantic_obligation":reuse.OBLIGATION,
  "v9_subject_id":reuse.V9_SUBJECT_ID,"v9_subject_sha256":reuse.V9_SUBJECT_SHA256,
  "policy_relevant_world_set_complete":True,"policy_cover_replay_pass":True}

def binding():
 return {"semantic_property_claim_id":reuse.PROPERTY_CLAIM_ID,"semantic_scope_claim_id":reuse.SCOPE_CLAIM_ID,
  "semantic_obligation":reuse.OBLIGATION,"target_scope_semantics":reuse.TARGET_SCOPE_SEMANTICS}

def fixture(root:Path,p=None):
 claim_src=SOURCE_ROOT/v.CLAIM_PATH; claim_dst=root/v.CLAIM_PATH
 claim_dst.parent.mkdir(parents=True,exist_ok=True);claim_dst.write_bytes(claim_src.read_bytes())
 p=p or problem()
 prob=write(root,"canonical/evidence/stable_r12_policy_cover_fixture.json",p)
 iv=write(root,"canonical/verification/stable_r12_policy_cover_fixture_verify.json",independent(p))
 recon_src=SOURCE_ROOT/reuse.R12_RECON_PATH;recon_dst=root/reuse.R12_RECON_PATH
 recon_dst.parent.mkdir(parents=True,exist_ok=True);recon_dst.write_bytes(recon_src.read_bytes())
 cert={"schema":v.CERT_SCHEMA,"claim_id":v.CLAIM_ID,
  **binding(),"v9_subject_id":reuse.V9_SUBJECT_ID,"v9_subject_sha256":reuse.V9_SUBJECT_SHA256,
  "real_exact_run":True,"content_addressed":True,
  "active_claim":{"path":v.CLAIM_PATH,"git_blob_sha":v.CLAIM_BLOB},
  "policy_cover_problem_ref":prob,"independent_cover_verification_ref":iv,
  "r12_reconciliation_ref":{"path":reuse.R12_RECON_PATH,"git_blob_sha":v._blob(recon_dst)},
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False}
 cp=root/"canonical/governance/cert.json";cp.parent.mkdir(parents=True,exist_ok=True)
 cp.write_text(json.dumps(cert,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 return cp,cert

class Tests(unittest.TestCase):
 def test_real_underlying_policy_cover_mechanism_passes_fixture(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cp,_=fixture(root)
   o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding())
   self.assertTrue(o["pass"],o);self.assertTrue(o["semantic_totality_verified"])
   self.assertTrue(o["cc_r3_material_totality_proved"]);self.assertFalse(o["c8_nonvacuity_proved"])
   self.assertFalse(o["semantic_truth_authority"]);self.assertFalse(o["terminal_authority"])
 def test_incomplete_world_set_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=problem();p["policy_cover_problem"]["world_set_completeness_receipt"]["policy_relevant_world_set_complete"]=False
   cp,_=fixture(root,p);o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding())
   self.assertFalse(o["pass"]);self.assertIn("V9_POLICY_COVER_REJECTED",o["reason"])
 def test_wrong_stable_claim_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cp,cert=fixture(root);cert["claim_id"]="wrong"
   cp.write_text(json.dumps(cert),encoding="utf-8")
   o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding())
   self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"STABLE_CLAIM_ID_MISMATCH")
 def test_authority_overclaim_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cp,cert=fixture(root);cert["semantic_truth_authority"]=True
   cp.write_text(json.dumps(cert),encoding="utf-8")
   o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding())
   self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"CERTIFICATE_AUTHORITY_OVERCLAIM")

if __name__=="__main__":unittest.main(verbosity=2)
