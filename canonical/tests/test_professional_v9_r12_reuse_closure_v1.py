from __future__ import annotations
import json,unittest
from pathlib import Path
from canonical.runtime import professional_v9_r12_reuse_closure_v1 as v
ROOT=Path(__file__).resolve().parents[2]

def auth(**extra):
 return {"independent_verified":True,"exact_byte_bound":True,"conclusion":"success",**extra}
def cover():
 sid="v9-mechanism-fixture"
 return {"state_id":sid,"worlds":[{"world_id":"w0"},{"world_id":"w1"}],
  "world_set_completeness_receipt":auth(policy_relevant_world_set_complete=True,state_id=sid),
  "policies":[{"policy_id":"p","adequate_world_ids":["w0","w1"],"cost_units":1,
   "adequacy_receipt":auth(policy_id="p",policy_adequate_on_every_listed_world=True,
    policy_safe_on_every_listed_world=True,hard_constraint_scope_complete=True,
    brain_owned=True,deployed_exact=True,resource_bound_proved=True)}],"discriminators":[]}
def problem():
 return {"semantic_property_claim_id":v.PROPERTY_CLAIM_ID,"semantic_scope_claim_id":v.SCOPE_CLAIM_ID,
  "semantic_obligation":v.OBLIGATION,"target_scope_semantics":v.TARGET_SCOPE_SEMANTICS,
  "v9_subject_id":v.V9_SUBJECT_ID,"v9_subject_sha256":v.V9_SUBJECT_SHA256,
  "real_exact_run":True,"content_addressed":True,"policy_cover_problem":cover()}
def verify_for(p):
 return {"pass":True,"independent_verified":True,"independent_verifier_id":"fixture-independent",
  "problem_sha256":v._digest(p),"semantic_property_claim_id":v.PROPERTY_CLAIM_ID,
  "semantic_scope_claim_id":v.SCOPE_CLAIM_ID,"semantic_obligation":v.OBLIGATION,
  "v9_subject_id":v.V9_SUBJECT_ID,"v9_subject_sha256":v.V9_SUBJECT_SHA256,
  "policy_relevant_world_set_complete":True,"policy_cover_replay_pass":True,
  "positive_route_observed":True}
def r12():return json.loads((ROOT/v.R12_RECON_PATH).read_text())

class Tests(unittest.TestCase):
 def test_c1_c7_reverified_on_exact_v9(self):
  o=v.verify_preserved_c1_c7()
  self.assertTrue(o["pass"],o);self.assertTrue(o["preserved_c1_c7_v9_reverified"])
  self.assertFalse(o["v9_c8_nonvacuity_proved"]);self.assertFalse(o["terminal_authority"])
 def test_cover_proves_bound_state_totality_but_not_claim_wide_cc_r3(self):
  p=problem();o=v.evaluate_v9_totality_cover(p,verify_for(p),r12_reconciliation=r12())
  self.assertTrue(o["pass"],o);self.assertFalse(o["v9_material_defeater_totality_proved"])
  self.assertTrue(o["v9_bound_state_material_defeater_totality_proved"]);self.assertFalse(o["cc_r3_terminal_closure_proved"]);self.assertFalse(o["v9_c8_nonvacuity_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])
 def test_positive_route_boolean_cannot_mint_c8(self):
  p=problem();iv=verify_for(p);iv["positive_route_observed"]=True
  o=v.evaluate_v9_totality_cover(p,iv,r12_reconciliation=r12())
  self.assertTrue(o["pass"]);self.assertFalse(o["v9_c8_nonvacuity_proved"])
 def test_incomplete_world_set_fails(self):
  p=problem();p["policy_cover_problem"]["world_set_completeness_receipt"]["policy_relevant_world_set_complete"]=False
  o=v.evaluate_v9_totality_cover(p,verify_for(p),r12_reconciliation=r12())
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"POLICY_COVER_TOTALITY_NOT_PROVED")
 def test_wrong_subject_fails(self):
  p=problem();p["v9_subject_id"]="V8"
  o=v.evaluate_v9_totality_cover(p,verify_for(p),r12_reconciliation=r12())
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"V9_COVER_BINDING_MISMATCH:v9_subject_id")
 def test_digest_drift_fails(self):
  p=problem();iv=verify_for(p);p["policy_cover_problem"]["policies"][0]["cost_units"]=2
  o=v.evaluate_v9_totality_cover(p,iv,r12_reconciliation=r12())
  self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"V9_COVER_INDEPENDENT_VERIFY_MISMATCH:problem_sha256")
 def test_no_quality_or_terminal_authority(self):
  p=problem();o=v.evaluate_v9_totality_cover(p,verify_for(p),r12_reconciliation=r12())
  self.assertFalse(o["quality_authority"]);self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
