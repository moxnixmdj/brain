from __future__ import annotations
import copy
import unittest

from canonical.runtime.objective_oracle_dominance_compiler import (
    SCHEMA,
    compile_dominance,
)

def base_contract():
    return {
        "behavior_id": "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
        "required_dimensions": ["TARGET", "FRESHNESS", "RECOVERY"],
        "dimensions": [
            {
                "id": "TARGET",
                "mechanism": "hidden admissible target/action oracle",
                "objective": True,
                "falsifiable": True,
                "hidden_from_candidate": True,
                "terminal_load_bearing": True,
            },
            {
                "id": "FRESHNESS",
                "mechanism": "state-version and stale-action rejection oracle",
                "objective": True,
                "falsifiable": True,
                "hidden_from_candidate": True,
                "terminal_load_bearing": True,
            },
            {
                "id": "RECOVERY",
                "mechanism": "forced mismatch then terminal rescue oracle",
                "objective": True,
                "falsifiable": True,
                "hidden_from_candidate": True,
                "terminal_load_bearing": True,
            },
        ],
        "candidate_receives_hidden_oracle": False,
        "weaker_comparator_dependency": "EXACT_OPUS_5_5",
        "route_gates": {
            "candidate_package_frozen": True,
            "executable_evaluator_bound": True,
            "population_or_source_pool_frozen": True,
            "information_boundary_frozen": True,
            "post_freeze_selector_frozen": True,
            "terminal_parent_binding_frozen": True,
            "independent_verification_pass": True,
        },
    }

class ObjectiveOracleDominanceCompilerTests(unittest.TestCase):
    def test_complete_route_can_delete_weaker_comparator_only_after_all_gates(self):
        out = compile_dominance({"schema": SCHEMA, "contracts": [base_contract()]})
        self.assertTrue(out["pass"])
        row = out["contracts"][0]
        self.assertTrue(row["objective_spec_complete"])
        self.assertTrue(row["weaker_comparator_structurally_unnecessary_if_route_verified"])
        self.assertTrue(row["weaker_comparator_deletion_authorized_now"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["capability_credit_delta"], 0)

    def test_open_verification_gate_preserves_comparator(self):
        c = base_contract()
        c["route_gates"]["independent_verification_pass"] = False
        out = compile_dominance({"schema": SCHEMA, "contracts": [c]})
        row = out["contracts"][0]
        self.assertTrue(row["objective_spec_complete"])
        self.assertFalse(row["weaker_comparator_deletion_authorized_now"])
        self.assertIn("independent_verification_pass", row["open_route_gates"])

    def test_missing_dimension_blocks_structural_dominance(self):
        c = base_contract()
        c["dimensions"] = c["dimensions"][:-1]
        out = compile_dominance({"schema": SCHEMA, "contracts": [c]})
        row = out["contracts"][0]
        self.assertFalse(row["objective_spec_complete"])
        self.assertEqual(row["missing_dimensions"], ["RECOVERY"])
        self.assertFalse(row["weaker_comparator_structurally_unnecessary_if_route_verified"])

    def test_nonobjective_dimension_blocks_dominance(self):
        c = base_contract()
        c["dimensions"][0]["objective"] = False
        out = compile_dominance({"schema": SCHEMA, "contracts": [c]})
        row = out["contracts"][0]
        self.assertFalse(row["objective_spec_complete"])
        self.assertEqual(row["incomplete_dimensions"][0]["id"], "TARGET")

    def test_hidden_oracle_leak_fails_closed(self):
        c = base_contract()
        c["candidate_receives_hidden_oracle"] = True
        out = compile_dominance({"schema": SCHEMA, "contracts": [c]})
        self.assertFalse(out["pass"])
        self.assertIn(
            "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001:CANDIDATE_HIDDEN_ORACLE_BOUNDARY_INVALID",
            out["errors"],
        )

    def test_duplicate_behavior_fails_closed(self):
        c = base_contract()
        out = compile_dominance({"schema": SCHEMA, "contracts": [c, copy.deepcopy(c)]})
        self.assertFalse(out["pass"])
        self.assertIn(
            "BEHAVIOR_ID_DUPLICATE:BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
            out["errors"],
        )

if __name__ == "__main__":
    unittest.main()
