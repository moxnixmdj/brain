from copy import deepcopy
from pathlib import Path
import json, unittest
from canonical.runtime import professional_r12_semantic_stable_roots_v1 as v

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
 def test_current_proves_only_r1_r2(self):
  o=v.verify(repo_root=ROOT)
  self.assertTrue(o["pass"],o)
  self.assertEqual(o["claim_id"],v.EXPECTED_R12_CLAIM_ID)
  self.assertTrue(o["cc_r1_reality_containment_proved"])
  self.assertTrue(o["cc_r2_mission_soundness_proved"])
  self.assertFalse(o["cc_r3_terminal_closure_proved"])
  self.assertFalse(o["r4_proof_closure"])
  self.assertFalse(o["semantic_property_truth_authority"])
 def test_scope_narrowing_fails(self):
  r,m=v._current_inputs(ROOT)
  r=deepcopy(r); r["scope_definition_sha256"]="0"*64
  o=v.evaluate_r12(r,m,scope_complete=True)
  self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"R12_SCOPE_BINDING_DRIFT")
 def test_acceptance_weakening_fails(self):
  r,m=v._current_inputs(ROOT)
  r=deepcopy(r); r["target_predicate"]["acceptance"]="MOST_CASES"
  o=v.evaluate_r12(r,m,scope_complete=True)
  self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"R12_ACCEPTANCE_DRIFT")
 def test_mission_correctness_drift_fails(self):
  r,m=v._current_inputs(ROOT)
  m=deepcopy(m); m["correctness_rule"]="BEST_EFFORT"
  o=v.evaluate_r12(r,m,scope_complete=True)
  self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"MISSION_CORRECTNESS_RULE_DRIFT")
 def test_old_claim_substitution_fails(self):
  r,m=v._current_inputs(ROOT)
  r=deepcopy(r); r["frozen_claim"]["claim_id"]=v.OLD_V2_R12_CLAIM_ID
  o=v.evaluate_r12(r,m,scope_complete=True)
  self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"R12_STABLE_CLAIM_ID_DRIFT")
 def test_scope_not_complete_fails(self):
  r,m=v._current_inputs(ROOT)
  o=v.evaluate_r12(r,m,scope_complete=False)
  self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"WHOLE_LEAF_SCOPE_NOT_COMPLETE")

if __name__=="__main__": unittest.main(verbosity=2)
