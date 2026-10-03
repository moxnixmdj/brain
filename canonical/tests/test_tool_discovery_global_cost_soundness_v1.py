from __future__ import annotations
import copy, unittest
from canonical.runtime import tool_discovery_global_cost_soundness_v1 as s

class Tests(unittest.TestCase):
    def test_complete_instance_satisfies_all_seven_contract_properties(self):
        out=s.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["interface_instance_verified"])
        self.assertEqual(set(out["interface_properties"]),s.REQUIRED_PROPERTIES)
        self.assertTrue(all(out["interface_properties"].values()))

    def test_v3_counterexample_is_real(self):
        out=s.evaluate()
        self.assertFalse(out["v3"]["globally_least_cost_sound"],out)
        self.assertEqual(out["v3"]["selected_cost"],10.0)
        self.assertEqual(out["v3"]["queried_sources"],["SRC_FIRST"])
        self.assertEqual(out["global_optimal_cost"],1.0)

    def test_v4_repairs_global_least_cost(self):
        out=s.evaluate()
        self.assertTrue(out["v4"]["globally_least_cost_sound"],out)
        self.assertEqual(out["v4"]["selected_cost"],1.0)
        self.assertEqual(out["v4"]["queried_sources"],["SRC_FIRST","SRC_SECOND"])

    def test_duplicate_source_id_fails_closed(self):
        inst=copy.deepcopy(s._load(s.INSTANCE))
        inst["sources"][1]["source_id"]="SRC_FIRST"
        out=s.evaluate(inst)
        self.assertFalse(out["interface_instance_verified"])
        self.assertTrue(out["status"].startswith("FAIL_CLOSED"))

    def test_hidden_truth_change_destroys_counterexample_not_silently_passes(self):
        inst=copy.deepcopy(s._load(s.INSTANCE))
        inst["hidden_capability_truth"]["urn:sealed-tool:1a4d3e-cheap"]["CAP_X"]=False
        out=s.evaluate(inst)
        self.assertFalse(str(out["status"]).startswith("PASS__COMPLETE_INTERFACE_INSTANCE"))

    def test_zero_credit_before_separate_acceptance_reduction(self):
        out=s.evaluate()
        self.assertTrue(out["acceptance_reduction_required_after_independent_verification"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_results_replayed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
