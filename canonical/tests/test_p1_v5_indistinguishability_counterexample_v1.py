from __future__ import annotations
import copy
import unittest
from canonical.runtime import p1_v5_indistinguishability_counterexample_v1 as ce

class Tests(unittest.TestCase):
    def test_live_counterexample_falsifies_one_shot_scope_superset(self):
        out=ce.evaluate()
        self.assertTrue(out["audit_valid"],out)
        self.assertTrue(out["public_payloads_identical"])
        self.assertTrue(out["correct_outputs_provably_different"])
        self.assertTrue(out["v5_deterministic_output_identical"])
        self.assertFalse(out["v5_passes_both_worlds"])
        self.assertFalse(out["one_shot_unique_identification_possible_under_current_information_boundary"])
        self.assertTrue(out["scope_superset_claim_falsified"])
        self.assertEqual(out["new_reality_units_consumed"],0)

    def test_pair_is_byte_equivalent_at_candidate_boundary(self):
        left,right=ce.construct_pair()
        self.assertEqual(ce.proof.public_task(left),ce.proof.public_task(right))
        self.assertNotEqual(left["_oracle"],right["_oracle"])
        self.assertNotEqual(left["_intervention_model"]["required_root_repairs"],right["_intervention_model"]["required_root_repairs"])

    def test_each_hidden_world_has_a_different_passing_identified_answer(self):
        left,right=ce.construct_pair()
        a=ce._identified_answer("A1","SCOPE")
        b=ce._identified_answer("A2","SCHEMA")
        self.assertTrue(ce.proof.score_case(left,a)["pass"])
        self.assertFalse(ce.proof.score_case(right,a)["pass"])
        self.assertTrue(ce.proof.score_case(right,b)["pass"])
        self.assertFalse(ce.proof.score_case(left,b)["pass"])

    def test_removing_declared_unique_rescuer_class_invalidates_audit(self):
        a=ce._load(ce.ABSOLUTE); m=ce._load(ce.MULTIPLEX); g=ce._load(ce.SCOPE_GATE)
        a=copy.deepcopy(a)
        a["population"]["classes"].remove(ce.DECLARED_CLASS)
        out=ce.evaluate(a,m,g)
        self.assertFalse(out["audit_valid"])
        self.assertIn("DECLARED_UNIQUE_RESCUER_CLASS_MISSING",out["errors"])

    def test_exposing_hidden_intervention_truth_does_not_count_as_current_boundary(self):
        a=ce._load(ce.ABSOLUTE); m=ce._load(ce.MULTIPLEX); g=ce._load(ce.SCOPE_GATE)
        m=copy.deepcopy(m)
        m["hidden_evaluator_information"].remove("HIDDEN_INTERVENTION_OUTCOMES_NOT_YET_EARNED")
        out=ce.evaluate(a,m,g)
        self.assertFalse(out["audit_valid"])
        self.assertIn("UNEARNED_INTERVENTION_OUTCOME_NOT_HIDDEN",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
