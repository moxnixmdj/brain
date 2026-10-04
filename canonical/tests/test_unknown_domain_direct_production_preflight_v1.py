from __future__ import annotations
import unittest
from canonical.runtime.unknown_domain_direct_production_preflight_v1 import preflight,LEAVES,TARGET

def base():
 return {
  "qualification_independent_pass":True,
  "exact_subject_blobs_rechecked":True,
  "production_cases_consumed":0,
  "production_beacon_generated":False,
  "candidate_mutated_after_qualification":False,
  "persistent_learned_bytes":0,
  "external_frontier_model_calls":0,
  "external_learned_capability_calls":0,
  "incremental_spend_usd":0,
  "target_predicate":TARGET,
  "authorized_leaves":sorted(LEAVES),
  "predicate_local_activation_independent_pass":True,
  "predicate_local_fresh_reality":True,
  "global_fresh_reality":False,
  "one_use_claim_created":False,
  "execution_started":False,
 }

class ProductionPreflightTests(unittest.TestCase):
 def test_ready_state_grants_no_authority_and_only_claim_next(self):
  out=preflight(base())
  self.assertTrue(out["ready"],out)
  self.assertEqual(out["status"],"READY_FOR_ATOMIC_ONE_USE_CLAIM_ONLY")
  self.assertFalse(out["execution_authority"])
 def test_missing_qualification_fails_closed(self):
  d=base(); d["qualification_independent_pass"]=False
  out=preflight(d); self.assertFalse(out["ready"])
  self.assertIn("V2_QUALIFICATION_NOT_INDEPENDENT_PASS",out["errors"])
 def test_global_authority_is_forbidden(self):
  d=base(); d["global_fresh_reality"]=True
  out=preflight(d); self.assertFalse(out["ready"])
  self.assertIn("GLOBAL_FRESH_REALITY_MUST_REMAIN_FALSE",out["errors"])
 def test_wrong_leaf_set_fails_closed(self):
  d=base(); d["authorized_leaves"]=d["authorized_leaves"][:1]
  out=preflight(d); self.assertFalse(out["ready"])
 def test_preexisting_claim_fails_closed_at_preflight(self):
  d=base(); d["one_use_claim_created"]=True
  out=preflight(d); self.assertFalse(out["ready"])
  self.assertIn("ONE_USE_CLAIM_MUST_NOT_EXIST_AT_PREFLIGHT",out["errors"])
 def test_nonzero_learned_or_model_usage_fails(self):
  d=base(); d["persistent_learned_bytes"]=1; d["external_frontier_model_calls"]=1
  out=preflight(d); self.assertFalse(out["ready"])

if __name__=="__main__":
 unittest.main(verbosity=2)
