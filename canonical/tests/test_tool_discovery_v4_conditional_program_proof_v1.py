from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_v4_conditional_program_proof_v1 as proof

class Tests(unittest.TestCase):
    def test_exact_conditional_program_proof_passes(self):
        out=proof.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["source_blob_drift"],[])
        self.assertTrue(out["interface_contract_property_set_exact"])
        self.assertTrue(all(out["structural_induction_obligations"].values()),out)
        self.assertTrue(out["exhaustive_dynamic_abstraction"]["pass"],out)
        self.assertGreater(out["exhaustive_dynamic_abstraction"]["checked"],1000)
        self.assertTrue(all(out["epoch_and_authority_checks"].values()),out)
        self.assertTrue(out["predicate_language_semantics"]["pass"],out)
        self.assertGreater(out["predicate_language_semantics"]["checked"],20)
        self.assertTrue(all(out["route_filter_checks"].values()),out)
        self.assertTrue(out["conditional_program_sound_under_v2_contract"])

    def test_oracle_is_global_not_visible_only(self):
        out=proof.evaluate()
        self.assertTrue(out["global_oracle_is_over_complete_tool_set_not_current_visible_subset"])

    def test_external_instance_remains_open_and_no_credit(self):
        out=proof.evaluate()
        self.assertFalse(out["universal_target_proved"])
        self.assertFalse(out["external_interface_instance_verified"])
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2",
        )
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
