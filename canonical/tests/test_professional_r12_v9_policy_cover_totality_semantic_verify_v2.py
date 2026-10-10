import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v2 as v

def binding():
 return {"semantic_property_claim_id":v.reuse.PROPERTY_CLAIM_ID,"semantic_scope_claim_id":v.reuse.SCOPE_CLAIM_ID,
  "semantic_obligation":v.reuse.OBLIGATION,"target_scope_semantics":v.reuse.TARGET_SCOPE_SEMANTICS}

def setup(root):
 claim=root/"claim.json";claim.write_text(json.dumps({"claim_id":v.CLAIM_ID}))
 problem=root/"problem.json";problem.write_text("{}")
 verify=root/"verify.json";verify.write_text("{}")
 recon=root/"recon.json";recon.write_text("{}")
 cert={"schema":v.CERT_SCHEMA,"claim_id":v.CLAIM_ID,**binding(),
  "v9_subject_id":v.reuse.V9_SUBJECT_ID,"v9_subject_sha256":v.reuse.V9_SUBJECT_SHA256,
  "real_exact_run":True,"content_addressed":True,
  "active_claim":{"path":v.CLAIM_PATH,"git_blob_sha":v.CLAIM_BLOB},
  "policy_cover_problem_ref":{"path":"canonical/evidence/p.json","git_blob_sha":"a"*40},
  "independent_cover_verification_ref":{"path":"canonical/verification/v.json","git_blob_sha":"b"*40},
  "r12_reconciliation_ref":{"path":"canonical/governance/r.json","git_blob_sha":"c"*40},
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False}
 cp=root/"cert.json";cp.write_text(json.dumps(cert))
 paths={v.CLAIM_PATH:claim,"canonical/evidence/p.json":problem,
  "canonical/verification/v.json":verify,"canonical/governance/r.json":recon}
 return cp,cert,paths

class Tests(unittest.TestCase):
 def test_schema_is_exact_v9_final_step_schema(self):
  self.assertEqual(v.CERT_SCHEMA,v.step_binding.TOTALITY_CERT_SCHEMA)
 @patch.object(v.reuse,"evaluate_v9_totality_cover")
 @patch.object(v,"_ref")
 def test_compatible_certificate_can_reach_policy_cover_verifier(self,ref,evaluate):
  evaluate.return_value={"pass":True,"v9_material_defeater_totality_proved":True,
   "cc_r3_terminal_closure_proved":True,"v9_c8_nonvacuity_proved":False}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cp,_,paths=setup(root)
   ref.side_effect=lambda _root,r,_prefixes: paths.get(r.get("path"))
   o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding())
   self.assertTrue(o["pass"],o);self.assertTrue(o["semantic_totality_verified"])
 @patch.object(v.reuse,"evaluate_v9_totality_cover")
 @patch.object(v,"_ref")
 def test_totality_cannot_mint_c8(self,ref,evaluate):
  evaluate.return_value={"pass":True,"v9_material_defeater_totality_proved":True,
   "cc_r3_terminal_closure_proved":True,"v9_c8_nonvacuity_proved":True}
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);cp,_,paths=setup(root);ref.side_effect=lambda _root,r,_prefixes: paths.get(r.get("path"))
   o=v.verify_certificate(root=root,certificate_path=cp,expected_binding=binding());self.assertFalse(o["pass"])

if __name__=="__main__":unittest.main(verbosity=2)
