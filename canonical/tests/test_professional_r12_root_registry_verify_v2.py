from __future__ import annotations
from copy import deepcopy
import json,unittest
from pathlib import Path
from canonical.runtime import professional_r12_root_registry_verify_v2 as v

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/v.REGISTRY_PATH

def reg():return json.loads(REG.read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
 def test_current_exact_registry_is_two_of_three(self):
  o=v.verify(repo_root=ROOT)
  self.assertTrue(o["pass"],o)
  self.assertEqual(o["proved_root_ids"],v.EXPECTED_PROVED)
  self.assertEqual(o["open_root_ids"],v.EXPECTED_OPEN)
  self.assertFalse(o["r4_proof_closure"])
  self.assertFalse(o["semantic_property_truth_authority"])

 def test_r4_cannot_be_flipped_true_with_cc_r3_open(self):
  d=reg();d["r4_proof_closure"]=True
  o=v.evaluate(d,repo_root=ROOT)
  self.assertFalse(o["pass"])
  self.assertTrue(any("R4_PROOF_CLOSURE_FLAG_DRIFT" in x or "R4_CLOSED_BEFORE_CC_R3" in x for x in o["errors"]))

 def test_old_mutable_pointer_claim_identity_fails(self):
  d=reg();d["active_claim"]["mission_blob_sha"]="6ab2147306a138f9ea327d8e19cb4a5bc76e89df"
  o=v.evaluate(d,repo_root=ROOT)
  self.assertFalse(o["pass"])
  self.assertTrue(any("MISSION_AUTHORITY_BINDING_STALE" in x for x in o["errors"]))

 def test_cc_r3_cannot_self_promote_without_payload(self):
  d=reg();d["certificate_slots"][2]["status"]="PROVED_CURRENT"
  d["currently_proved_root_certificates"]=3;d["currently_open_root_certificates"]=0;d["r4_proof_closure"]=True
  o=v.evaluate(d,repo_root=ROOT)
  self.assertFalse(o["pass"])
  self.assertTrue(any("PROVED_SLOT_CERTIFICATE_MISSING:CC_R3_TERMINAL_CLOSURE_V1" in x for x in o["errors"]))

if __name__=="__main__":unittest.main(verbosity=2)
