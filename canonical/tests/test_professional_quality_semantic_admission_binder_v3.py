from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from canonical.runtime import professional_quality_semantic_admission_binder_v3 as b

CLAIM={"claim":{"claim_kind":"PROPERTY_CERTIFICATE","claim_id":"c"*64,
 "scope_sha256":"s"*64,"target_predicate_sha256":"t"*64,"semantics_sha256":"m"*64}}
def receipt(root:Path):
 p=root/"canonical/evidence/x.json";p.parent.mkdir(parents=True,exist_ok=True)
 basis={"pass":True,"independent_verified":True,"leaf_id":"L","root_id":"R",
  "semantic_claim_id":"c"*64,"semantic_scope_sha256":"s"*64,
  "semantic_target_predicate_sha256":"t"*64,"semantic_semantics_sha256":"m"*64,
  "claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,
  "r4_proof_realization_authority":True}
 import json;p.write_text(json.dumps(basis))
 return {"schema":b.RECEIPT_SCHEMA,"leaf_id":"L","root_id":"R","leaf_kind":"SEMANTIC",
  "verdict":"PASS","closure_scope":"EXACT_LEAF","acceptance_sha256":b.semantic_sha("A"),
  "root_contract_sha256":b.semantic_sha("C"),"manifest_git_blob_sha":"g",
  "leaf_semantic_satisfied":True,"semantic_claim_id":"c"*64,"semantic_scope_sha256":"s"*64,
  "semantic_target_predicate_sha256":"t"*64,"semantic_semantics_sha256":"m"*64,
  "claim_scoped_totality_proved":True,"cc_r1_reality_containment_proved":True,
  "cc_r2_mission_soundness_proved":True,"cc_r3_terminal_closure_proved":True,
  "r4_proof_realization_authority":True,"terminal_authority":False,
  "verification_basis":[{"path":"canonical/evidence/x.json","git_blob_sha":b.git_blob_sha(p)}]}
def check(r,root):
 return b.validate_semantic_receipt(r,CLAIM,leaf_id="L",root_id="R",acceptance="A",contract="C",
  manifest_git_blob_sha="g",repo_root=root)

class Tests(unittest.TestCase):
 def test_exact_receipt_passes(self):
  with tempfile.TemporaryDirectory() as d:
   o=check(receipt(Path(d)),Path(d));self.assertTrue(o["pass"],o)
   self.assertTrue(o["positive_semantic_admission_authorized"])
   self.assertFalse(o["semantic_leaf_property_truth_authority"]);self.assertFalse(o["terminal_authority"])
 def test_each_totality_field_is_mandatory(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for field in b.REQUIRED_TOTALITY_FIELDS:
    r=receipt(root);r[field]=False
    o=check(r,root);self.assertFalse(o["pass"],(field,o))
 def test_each_claim_binding_is_exact(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   fields=["semantic_claim_id","semantic_scope_sha256","semantic_target_predicate_sha256","semantic_semantics_sha256"]
   for field in fields:
    r=receipt(root);r[field]="x"*64
    self.assertFalse(check(r,root)["pass"],field)
 def test_stale_basis_fails(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=receipt(root);r["verification_basis"][0]["git_blob_sha"]="0"*40
   self.assertFalse(check(r,root)["pass"])
 def test_current_but_semantically_unverified_basis_fails(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=receipt(root);p=root/"canonical/evidence/x.json";p.write_text("{}")
   r["verification_basis"][0]["git_blob_sha"]=b.git_blob_sha(p)
   o=check(r,root);self.assertFalse(o["pass"])
   self.assertIn("INDEPENDENT_SEMANTIC_TOTALITY_BASIS_REQUIRED",o["errors"])
 def test_bad_leaf_root_acceptance_contract_and_authority_fail(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for field,value in [("leaf_id","X"),("root_id","X"),("acceptance_sha256","X"),
                       ("root_contract_sha256","X"),("terminal_authority",True)]:
    r=receipt(root);r[field]=value;self.assertFalse(check(r,root)["pass"],field)
 def test_structural_shape_has_no_downstream_authority(self):
  o=b.prove_fail_closed_shape();self.assertTrue(o["pass"])
  self.assertFalse(o["quality_authority"]);self.assertFalse(o["acceptance_authority"])
  self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
