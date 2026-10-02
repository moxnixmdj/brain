from __future__ import annotations
import copy
import unittest
from canonical.runtime.terminal_scope_quarantine_propagation_v1 import (
    REGISTRY, REDUCTION, SCOPE_RECEIPT, evaluate, load
)

class Tests(unittest.TestCase):
    def docs(self):
        return load(REGISTRY),load(REDUCTION),load(SCOPE_RECEIPT)

    def test_live_p1_quarantine_propagates_exactly(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["contract_accounting"]["whole_scope_pass_count_after_quarantine"],11)
        self.assertEqual(out["family_accounting"]["unaffected_behavioral_pass_count"],11)
        self.assertEqual(out["family_accounting"]["quarantined_family_count"],8)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",out["family_accounting"]["quarantined_families"])
        self.assertNotIn("TOOL_DISCOVERY_SELECTION_AND_LEARNING",out["family_accounting"]["quarantined_families"])

    def test_broad_transport_true_fails_closed(self):
        registry,reduction,receipt=self.docs()
        receipt=copy.deepcopy(receipt)
        receipt["broad_p1_transport_admissible"]=True
        out=evaluate(registry,reduction,receipt)
        self.assertFalse(out["pass"])
        self.assertIn("BROAD_P1_TRANSPORT_NOT_QUARANTINED",out["errors"])

    def test_family_mapping_drift_fails_closed(self):
        registry,reduction,receipt=self.docs()
        registry=copy.deepcopy(registry)
        registry["family_to_residual_contracts"]["TOOL_DISCOVERY_SELECTION_AND_LEARNING"].append("TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001")
        out=evaluate(registry,reduction,receipt)
        self.assertFalse(out["pass"])
        self.assertIn("P1_DEPENDENT_FAMILY_SET_DRIFT",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
