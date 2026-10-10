from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import professional_semantic_safety_adequacy_normal_form_v1 as n

class Tests(unittest.TestCase):
 def test_current_repaired_normal_form_mechanisms_ready(self):
  out=n.verify()
  self.assertTrue(out["pass"],out)
  self.assertEqual(out["old_overstrong_semantic_spec_falsified_count"],12)
  self.assertEqual(out["semantic_credit_safety_mechanism_ready_count"],12)
  self.assertTrue(out["adequacy_gap_classifier_verified"])
  self.assertTrue(out["minimum_information_policy_verified"])
  self.assertFalse(out["abstention_is_capability_success"])
  self.assertEqual(out["repaired_semantic_property_truth_proved_count"],0)
  self.assertFalse(out["terminal_authority"])

 def test_credit_safety_rejects_each_load_bearing_mutation(self):
  pack=n.pack_v3.verify()
  self.assertTrue(pack["pass"],pack)
  claim=pack["claims"][0]
  good=n._good_semantic_receipt(claim)
  self.assertEqual(n.binder._semantic_receipt_errors(good,claim),[])
  for field,bad in {
   "semantic_claim_id":"0"*64,
   "semantic_scope_sha256":"0"*64,
   "semantic_target_predicate_sha256":"0"*64,
   "semantic_semantics_sha256":"0"*64,
   "claim_scoped_totality_proved":False,
   "cc_r1_reality_containment_proved":False,
   "cc_r2_mission_soundness_proved":False,
   "cc_r3_terminal_closure_proved":False,
   "r4_proof_realization_authority":False,
  }.items():
   row=dict(good);row[field]=bad
   self.assertTrue(n.binder._semantic_receipt_errors(row,claim),field)

 def test_constructive_gap_cannot_be_relabelled_external(self):
  row=n.reality.compile_gap_contract(n._closure(internal=["MISSING_CAPABILITY"],external=True))
  self.assertEqual(row["gap_class"],"CONSTRUCTIVE_CAPABILITY_GAP")

 def test_evidence_gap_remains_acquisition_work(self):
  row=n.reality.compile_gap_contract(n._closure(evidence=["MISSING_EVIDENCE"],pending=True))
  self.assertEqual(row["gap_class"],"PENDING_ACQUISITION_OR_EXPERIMENT")

 def test_externality_requires_passed_closure_not_current_absence(self):
  row=n.reality.compile_gap_contract(n._closure(external=True,passed=False))
  self.assertNotEqual(row["gap_class"],"PROVEN_INFORMATION_THEORETICALLY_EXTERNAL")
  ext=n.reality.compile_gap_contract(n._closure(external=True,passed=True))
  self.assertEqual(ext["gap_class"],"PROVEN_INFORMATION_THEORETICALLY_EXTERNAL")

 def test_minimum_information_never_defaults_to_full_benchmark(self):
  gap=n.reality.compile_gap_contract(n._closure(evidence=["E1"],pending=True))
  d=n.reality.compile_decision_sufficient_contract(gap)
  m=n.reality.compile_minimum_information_contract(gap,d)
  self.assertEqual(m["request_count"],1)
  self.assertTrue(m["requests"][0]["broad_acquisition_forbidden_without_minimality_proof"])
  self.assertEqual(m["proof_precedence"][-1],"FULL_EMPIRICAL_EVALUATION_LAST")

if __name__=="__main__":unittest.main(verbosity=2)
