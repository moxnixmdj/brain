from __future__ import annotations
import copy
import unittest

from canonical.runtime import p1_v5_causal_identifiability_falsifier_v1 as f
from canonical.runtime import p1_v5_direct_surface_scope_superset_v1 as superset

class Tests(unittest.TestCase):
    def test_exact_twin_world_counterexample_falsifies_v5(self):
        out=f.evaluate()
        self.assertTrue(out["falsified"],out)
        self.assertTrue(out["identical_public_payload_across_hidden_worlds"])
        self.assertEqual(out["hidden_world_count"],2)
        self.assertEqual(out["hidden_cause_count"],2)
        self.assertTrue(out["candidate_forces_unique_cause"])
        self.assertEqual(sum(x["candidate_pass"] for x in out["world_results"]),1)

    def test_v5_selects_earliest_failed_step_and_wrong_repair_in_late_world(self):
        out=f.evaluate()
        cand=out["candidate_output"]
        self.assertEqual(cand["status"],"IDENTIFIED")
        self.assertEqual(cand["cause_action_id"],"A1")
        self.assertEqual(cand["repair_targets"],["restore:A1:AUTHORITY"])
        late=next(x for x in out["world_results"] if x["world_id"]=="LATE_STATE_CAUSAL")
        self.assertFalse(late["candidate_pass"])

    def test_public_payload_contains_no_hidden_world_or_intervention_truth(self):
        public=f.public_case()
        s=str(public)
        self.assertNotIn("EARLY_AUTHORITY_CAUSAL",s)
        self.assertNotIn("LATE_STATE_CAUSAL",s)
        self.assertNotIn("true_cause_action_id",s)
        self.assertNotIn("rescuing_repairs",s)

    def test_existing_scope_superset_gate_is_false_positive_under_counterexample(self):
        old=superset.evaluate()
        self.assertTrue(old["pass"],old)
        self.assertTrue(f.evaluate()["falsified"])

if __name__=="__main__":
    unittest.main(verbosity=2)
