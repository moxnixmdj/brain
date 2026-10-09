from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
CURRENT=ROOT/"canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json"
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ONE=ROOT/"canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"
WRAPPER=ROOT/"canonical/runtime/r2_direct_live_admission_v1.py"
V19=ROOT/"canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"
V20=ROOT/"canonical/runtime/r2_direct_end_to_end_adequacy_v20.py"
FIXED=ROOT/"canonical/runtime/general_adequate_decision_fixed_point_v2.py"
FABRIC=ROOT/"canonical/runtime/unified_cognitive_fabric_v1.py"
ONE_RUNTIME=ROOT/"canonical/runtime/one_shot_reality_closure_v2.py"
V20_VERIFY=ROOT/"canonical/verification/R2_COMPOSITIONAL_NATURAL_EFFECT_LATTICE_V20_VERIFY_20261009_V1.json"
DYN_POINTER=ROOT/"canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json"
DYN_MANIFEST=ROOT/"canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json"

def blob(path:Path)->str:
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path:Path):
 return json.loads(path.read_text(encoding="utf-8"))

class CurrentDefaultRuntimeIntegrationV1Tests(unittest.TestCase):
 def test_current_binding_is_exact_and_fail_closed(self):
  c=load(CURRENT)
  self.assertEqual(c["schema"],"PROJECT_BRAIN_CURRENT_DEFAULT_RUNTIME_INTEGRATION_V1")
  self.assertTrue(c["canonical_front_door"]["auto_one_shot_fallback_live"])
  self.assertEqual(c["canonical_front_door"]["git_blob_sha"],blob(FABRIC))
  self.assertTrue(c["canonical_front_door"]["exact_original_decision_replay_required"])
  self.assertTrue(c["canonical_front_door"]["externality_pass_is_not_task_success"])

  rt=c["r2_default_route_runtime"]
  self.assertEqual(rt["stable_wrapper_git_blob_sha"],blob(WRAPPER))
  self.assertEqual(rt["fixed_point_controller_git_blob_sha"],blob(FIXED))
  self.assertEqual(rt["v57_activation_baseline"]["runtime_git_blob_sha"],blob(V19))
  self.assertEqual(rt["v57_activation_baseline"]["route_count"],39)
  self.assertEqual(rt["verified_successor"]["runtime_git_blob_sha"],blob(V20))
  self.assertEqual(rt["verified_successor"]["verification_git_blob_sha"],blob(V20_VERIFY))
  self.assertEqual(rt["verified_successor"]["static_default_route_count_before_dynamic"],40)
  self.assertEqual(rt["dynamic_admission"]["current_manifest_git_blob_sha"],blob(DYN_MANIFEST))
  self.assertEqual(rt["dynamic_admission"]["current_dynamic_route_count"],0)
  self.assertFalse(rt["dynamic_admission"]["future_verified_route_requires_new_vN_source"])

  one=c["one_shot_fallback"]
  self.assertEqual(one["runtime_git_blob_sha"],blob(ONE_RUNTIME))
  self.assertTrue(one["fixed_point_success_required_before_replay"])
  self.assertTrue(one["proven_externality_does_not_authorize_task_success"])
  self.assertFalse(one["explicit_adequate_decision_auto_fallback"])
  self.assertFalse(one["user_clarification_auto_fallback"])
  self.assertFalse(c["terminal_authority"])

 def test_r2_pointer_preserves_v57_snapshot_but_binds_default_runtime(self):
  r2=load(R2); d=r2["direct_adequacy"]
  self.assertEqual(d["current_route_count"],39)
  self.assertEqual(d["bounded_family_count"],36)
  self.assertEqual(d["current_route_count_role"],"FROZEN_V57_ACTIVATION_AND_SCHEDULER_BASELINE_ONLY")
  self.assertEqual(d["fixed_point_controller_git_blob_sha"],blob(FIXED))
  self.assertEqual(r2["controller"]["fixed_point_git_blob_sha"],blob(FIXED))
  live=d["default_runtime_integration"]
  self.assertEqual(live["path"],"canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json")
  self.assertEqual(live["stable_wrapper_git_blob_sha"],blob(WRAPPER))
  self.assertEqual(live["verified_static_backend_git_blob_sha"],blob(V20))
  self.assertEqual(live["static_default_route_count_before_dynamic"],40)
  self.assertEqual(live["dynamic_admission_pointer_path"],"canonical/governance/CURRENT_R2_DIRECT_ROUTE_ADMISSIONS.json")
  self.assertFalse(live["future_route_source_version_edit_required"])

 def test_dynamic_current_pointer_binds_exact_empty_manifest(self):
  p=load(DYN_POINTER)
  self.assertEqual(p["target"]["path"],"canonical/governance/R2_DIRECT_ROUTE_DYNAMIC_ADMISSIONS_20261009_V1.json")
  self.assertEqual(p["target"]["git_blob_sha"],blob(DYN_MANIFEST))
  m=load(DYN_MANIFEST)
  self.assertEqual(m["admission_count"],0)
  self.assertEqual(m["admissions"],[])

 def test_one_shot_pointer_no_longer_claims_not_auto_default(self):
  one=load(ONE)
  self.assertNotIn("NOT_AUTO_DEFAULT",one["status"])
  self.assertIn("AUTO_DEFAULT_FALLBACK_LIVE",one["status"])
  self.assertFalse(one["authority"]["live_default_entrypoint"])
  self.assertTrue(one["authority"]["auto_default_fallback"])
  self.assertTrue(one["authority"]["auto_default_fallback_exact_replay_required"])
  self.assertTrue(one["authority"]["auto_default_fallback_externality_is_not_task_success"])
  self.assertEqual(one["frontdoor_binding"]["git_blob_sha"],blob(FABRIC))
  self.assertEqual(
   one["frontdoor_binding"]["role"],
   "META_ORCHESTRATOR_AUTO_FALLBACK_AFTER_NORMAL_R2__NOT_PRIMARY_ROUTER",
  )

if __name__=="__main__":
 unittest.main(verbosity=2)
