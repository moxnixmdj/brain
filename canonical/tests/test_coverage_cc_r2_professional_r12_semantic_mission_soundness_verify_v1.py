from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import coverage_cc_r2_professional_r12_semantic_mission_soundness_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load(path:str):
 return json.loads((ROOT/path).read_text(encoding="utf-8"))

def docs():
 return {
  "manifest":load(v.MANIFEST_PATH),
  "frozen":load(v.CLAIM_PATH),
  "certificate":load(v.CERT_PATH),
  "mission":load(v.MISSION_PATH),
  "closure":load(v.CLOSURE_PATH),
  "identity_activation":load(v.IDENTITY_ACTIVATION_PATH),
  "identity_verification":load(v.IDENTITY_VERIFY_PATH),
 }

class R12SemanticCC_R2MissionSoundnessTests(unittest.TestCase):
 def evaluate(self,d):
  return v.evaluate_documents(
   manifest=d["manifest"],frozen=d["frozen"],certificate=d["certificate"],
   mission=d["mission"],closure=d["closure"],
   identity_activation=d["identity_activation"],
   identity_verification=d["identity_verification"],
  )

 def test_exact_current_r12_claim_proves_cc_r2_only(self):
  out=v.verify()
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["cc_r2_mission_soundness_proved"])
  self.assertTrue(out["g_minus_subseteq_g_real"])
  self.assertTrue(out["material_unresolved_premise_positive_credit_forbidden"])
  self.assertTrue(out["decision_null_residual_allowed"])
  self.assertTrue(out["abstention_zero_property_credit"])
  self.assertFalse(out["r12_semantic_property_truth_authority"])
  self.assertFalse(out["professional_quality_closure_implied"])
  self.assertFalse(out["terminal_authority"])

 def test_frozen_claim_id_substitution_fails_closed(self):
  d=docs();d["frozen"]["claim_id"]="0"*64
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("FROZEN_CLAIM_FIELD_DRIFT:claim_id",out["errors"])

 def test_frozen_claim_scope_narrowing_fails_closed(self):
  d=docs()
  d["frozen"]["claim_scope"]["scope_definition"]["domain_definition"]["filters"]=["ONLY_EASY_CASES"]
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("FROZEN_CLAIM_SCOPE_NOT_EXACT_CANONICAL_SCOPE",out["errors"])

 def test_acceptance_weakening_fails_closed(self):
  d=docs();d["frozen"]["target_predicate"]["acceptance"]="MOST_CASES_LOOK_FINE"
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("FROZEN_ACCEPTANCE_DRIFT",out["errors"])

 def test_mission_correctness_axiom_drift_fails_closed(self):
  d=docs();d["mission"]["correctness_rule"]="BEST_EFFORT_VERIFICATION"
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("MISSION_CORRECTNESS_AXIOM_DRIFT",out["errors"])

 def test_missing_decision_null_rule_fails_closed(self):
  d=docs()
  d["closure"]["closure_rule"]["necessary"]=[
   x for x in d["closure"]["closure_rule"]["necessary"]
   if x!="RESIDUAL_UNKNOWN_DOES_NOT_CHANGE_THE_AUTHORIZED_DECISION"
  ]
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertTrue(any(x.startswith("CLOSURE_NORMAL_FORM_REQUIRED_RULES_MISSING:") for x in out["errors"]))

 def test_missing_certificate_or_abstain_route_fails_closed(self):
  d=docs()
  d["closure"]["p1_default_profile"]["steps"]=[
   x for x in d["closure"]["p1_default_profile"]["steps"]
   if x!="ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT"
  ]
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("CLOSURE_NORMAL_FORM_ABSTENTION_ROUTE_MISSING",out["errors"])

 def test_identity_carrier_claim_drift_fails_closed(self):
  d=docs();d["identity_activation"]["current_state"]["r12_claim_id"]="0"*64
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("IDENTITY_CARRIER_R12_CLAIM_DRIFT",out["errors"])

 def test_unauthorized_mission_axiom_in_reduction_fails_closed(self):
  d=docs();d["certificate"]["reduction"][0]["mission_axioms"]=["M_VERIFY","M_MAGIC"]
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("REDUCTION_UNAUTHORIZED_AXIOM_SET:"+v.REQUIREMENTS[0],out["errors"])

 def test_certificate_cannot_self_grant_property_truth(self):
  d=docs();d["certificate"]["r12_semantic_property_truth_authority"]=True
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:r12_semantic_property_truth_authority",out["errors"])

 def test_theorem_cannot_inflate_to_global_mission_completion(self):
  d=docs();d["certificate"]["theorem"]["global_mission_completion_implied"]=True
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("THEOREM_OVERCLAIM:global_mission_completion_implied",out["errors"])

 def test_nonvacuity_requirement_cannot_be_removed(self):
  d=docs()
  d["frozen"]["target_predicate"]["requires"]=d["frozen"]["target_predicate"]["requires"][:-1]
  out=self.evaluate(d)
  self.assertFalse(out["pass"])
  self.assertIn("FROZEN_REQUIREMENT_SET_OR_ORDER_DRIFT",out["errors"])

if __name__=="__main__":
 unittest.main(verbosity=2)
