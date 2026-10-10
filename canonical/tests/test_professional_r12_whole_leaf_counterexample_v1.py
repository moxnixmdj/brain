import unittest
from unittest.mock import patch
from canonical.runtime import professional_r12_whole_leaf_counterexample_v1 as v

class Tests(unittest.TestCase):
 def test_current_real_task_proves_constructive_counterexample(self):
  o=v.verify()
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["constructive_counterexample_proved"])
  self.assertTrue(o["original_universal_predicate_falsified"])
  self.assertTrue(o["specification_repair_authorized"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertFalse(o["terminal_authority"])

 @patch.object(v.v9,"route")
 def test_no_counterexample_if_missing_evidence_state_does_not_abstain(self,route):
  route.return_value={
   "status":"ROUTE__P1_ORDINARY",
   "positive_certification_authorized":True,
   "final_step_outcome":"POSITIVE_CERTIFICATE",
  }
  o=v.verify()
  self.assertFalse(o["pass"])
  self.assertEqual(o["reason"],"MISSING_EVIDENCE_STATE_DID_NOT_ABSTAIN")

 @patch.object(v.sb,"run_context_digest")
 def test_real_task_context_must_match_independent_replay(self,digest):
  digest.return_value="sha256:wrong"
  o=v.verify()
  self.assertFalse(o["pass"])
  self.assertEqual(o["reason"],"REAL_TASK_RUN_CONTEXT_RECONSTRUCTION_MISMATCH")

 def test_repaired_predicate_preserves_abstention_and_nonvacuity(self):
  o=v.verify()
  self.assertIn("EXPLICIT_FAIL_CLOSED_ABSTENTION",o["recommended_repaired_predicate"])
  self.assertIn("NONVACUOUS_REAL_POSITIVE_ROUTE",o["recommended_repaired_predicate"])
  self.assertFalse(o["new_primitive_required"])

if __name__=="__main__":unittest.main(verbosity=2)
