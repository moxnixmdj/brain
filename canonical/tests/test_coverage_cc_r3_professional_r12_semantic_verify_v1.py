import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v1 as v
SRC=Path(__file__).resolve().parents[2]

def put(root,rel,obj):
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj)+"\n")
 return {"path":rel,"git_blob_sha":v._blob(p)}

def fx(root):
 cp=root/v.CLAIM_PATH;cp.parent.mkdir(parents=True,exist_ok=True);cp.write_bytes((SRC/v.CLAIM_PATH).read_bytes())
 active=json.loads(cp.read_text())
 vp=root/v.TOTALITY_VERIFIER_PATH;vp.parent.mkdir(parents=True,exist_ok=True);vp.write_bytes((SRC/v.TOTALITY_VERIFIER_PATH).read_bytes())
 tc=put(root,"canonical/governance/t.json",{"x":1})
 tv={"path":v.TOTALITY_VERIFIER_PATH,"git_blob_sha":v._blob(vp)}
 tr=put(root,"canonical/verification/t.json",{"x":1})
 state={v.v9.base.STEP_BINDINGS_KEY:{v.v9.base.FINAL_STEP:{
  "material_totality_certificate":tc,"material_totality_semantic_verifier":tv,
  "material_totality_semantic_verification":tr}}}
 sr=put(root,"canonical/evidence/state.json",state)
 cert={"schema":v.CERT_SCHEMA,"root_id":v.ROOT_ID,"claim_id":v.CLAIM_ID,
  "active_claim":{"path":v.CLAIM_PATH,"git_blob_sha":v.CLAIM_BLOB},
  "material_totality_certificate":tc,"material_totality_semantic_verifier":tv,
  "material_totality_semantic_verification":tr,"v9_route_state":sr,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"accounting":{"terminal_credit_delta":0}}
 cpath=root/"canonical/governance/r3.json";cpath.write_text(json.dumps(cert))
 return active,cpath,cert,state

def pos():
 return {"final_step_outcome":"POSITIVE_CERTIFICATE","positive_certification_authorized":True,
  "v9_executable_r12_totality_semantics_verified":True,
  "r12_totality_semantic_verification":{"pass":True,"semantic_totality_verified":True,
   "semantic_property_claim_id":v.totality_verify.reuse.PROPERTY_CLAIM_ID}}

class Tests(unittest.TestCase):
 @patch.object(v.v9,"route")
 def test_positive_exact_binding(self,r):
  r.return_value=pos()
  with tempfile.TemporaryDirectory() as d:
   a,c,_,_=fx(Path(d));o=v.verify_certificate(root=Path(d),certificate_path=c,active_claim=a,root_id=v.ROOT_ID)
   self.assertTrue(o["pass"],o);self.assertTrue(o["cc_r3_terminal_closure_proved"])
 @patch.object(v.v9,"route")
 def test_abstain_fails(self,r):
  r.return_value={"final_step_outcome":"ABSTAIN","positive_certification_authorized":False}
  with tempfile.TemporaryDirectory() as d:
   a,c,_,_=fx(Path(d));o=v.verify_certificate(root=Path(d),certificate_path=c,active_claim=a,root_id=v.ROOT_ID)
   self.assertFalse(o["pass"])
 @patch.object(v.v9,"route")
 def test_witness_mismatch_fails(self,r):
  r.return_value=pos()
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,c,cert,state=fx(root)
   state[v.v9.base.STEP_BINDINGS_KEY][v.v9.base.FINAL_STEP]["material_totality_certificate"]={"path":"canonical/governance/x.json","git_blob_sha":"a"*40}
   p=root/cert["v9_route_state"]["path"];p.write_text(json.dumps(state));cert["v9_route_state"]["git_blob_sha"]=v._blob(p);c.write_text(json.dumps(cert))
   o=v.verify_certificate(root=root,certificate_path=c,active_claim=a,root_id=v.ROOT_ID);self.assertFalse(o["pass"])

if __name__=="__main__":unittest.main(verbosity=2)
