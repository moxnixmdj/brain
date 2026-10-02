from __future__ import annotations
import unittest
from canonical.runtime import p1_v5_causal_soundness_veto_v1 as veto

class P1V5CausalSoundnessVetoTests(unittest.TestCase):
    def test_false_earliest_counterexample_reproduces(self):
        out=veto.evaluate()
        self.assertTrue(out["route_falsified"],out)
        self.assertEqual(out["v5_output"]["cause_action_ids"],["A1"])
        self.assertEqual(out["v5_output"]["mechanism_classes"],["SCOPE"])
        self.assertFalse(out["executable_outcomes"]["baseline_success"])
        self.assertFalse(out["executable_outcomes"]["repair_early_scope_success"])
        self.assertTrue(out["executable_outcomes"]["repair_later_state_transition_success"])
        self.assertEqual(out["required_true_cause_action"],"A4")
        self.assertFalse(out["p1_v5_scope_superset_admissible"])
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
