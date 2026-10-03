from __future__ import annotations

import copy
import unittest

from canonical.runtime.tool_discovery_matched_route_precondition_reducer_v1 import (
    FREEZE,
    INTERNAL,
    PROTOCOLS,
    REDUCTION,
    _load,
    evaluate,
)


class ToolDiscoveryMatchedRoutePreconditionReducerV1Tests(unittest.TestCase):
    def setUp(self):
        self.freeze = _load(FREEZE)
        self.internal = _load(INTERNAL)
        self.protocols = _load(PROTOCOLS)
        self.reduction = _load(REDUCTION)

    def test_live_sources_reduce_exactly_three_preconditions_zero_credit(self):
        out = evaluate(self.freeze, self.internal, self.protocols, self.reduction)
        self.assertTrue(out["precondition_reduction_proved"])
        self.assertTrue(out["tree_checker_population_freeze_proved"])
        self.assertTrue(out["internal_composition_basis_proved"])
        self.assertTrue(out["fixed_full_population_selector_accounting_proved"])
        self.assertEqual(out["closed_precondition_count"], 3)
        self.assertEqual(out["remaining_precondition_count"], 3)
        self.assertFalse(out["toolathlon_result_observed"])
        self.assertFalse(out["tool_discovery_acceptance_granted"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_tree_identity_is_load_bearing(self):
        mutant = copy.deepcopy(self.freeze)
        mutant["benchmark_identity"]["finalpool_tree_sha"] = ""
        out = evaluate(mutant, self.internal, self.protocols, self.reduction)
        self.assertFalse(out["precondition_reduction_proved"])
        self.assertIn("CONTENT_ADDRESSED_TASK_CHECKER_FREEZE_NOT_PROVED", out["errors"])

    def test_all_108_evaluators_are_load_bearing(self):
        mutant = copy.deepcopy(self.freeze)
        mutant["benchmark_identity"]["task_file_presence"]["evaluation/main.py"] = 107
        out = evaluate(mutant, self.internal, self.protocols, self.reduction)
        self.assertFalse(out["precondition_reduction_proved"])
        self.assertIn("CONTENT_ADDRESSED_TASK_CHECKER_FREEZE_NOT_PROVED", out["errors"])

    def test_independent_internal_receipt_is_load_bearing(self):
        mutant = copy.deepcopy(self.internal)
        mutant["workflow_conclusion"] = "failure"
        out = evaluate(self.freeze, mutant, self.protocols, self.reduction)
        self.assertFalse(out["precondition_reduction_proved"])
        self.assertIn("INDEPENDENT_INTERNAL_COMPOSITION_BASIS_NOT_PROVED", out["errors"])

    def test_transfer_fact_is_load_bearing(self):
        mutant = copy.deepcopy(self.internal)
        mutant["verified"].remove("VALID_PRIOR_CAPABILITY_EVIDENCE_REUSED_ON_LATER_TASK")
        out = evaluate(self.freeze, mutant, self.protocols, self.reduction)
        self.assertFalse(out["precondition_reduction_proved"])
        self.assertIn("INDEPENDENT_INTERNAL_COMPOSITION_BASIS_NOT_PROVED", out["errors"])

    def test_85_is_the_minimum_integer_threshold_for_reported_77_8_bar(self):
        good = evaluate(self.freeze, self.internal, self.protocols, self.reduction)
        self.assertTrue(good["fixed_full_population_selector_accounting_proved"])
        mutant = copy.deepcopy(self.reduction)
        for row in mutant["reductions"]:
            if row["prior_open_precondition"] == "FREEZE_TERMINAL_ACCEPTANCE_ACCOUNTING_AND_SELECTOR":
                row["accounting"]["minimum_integer_brain_passes_to_meet_or_exceed_reported_bar"] = 84
        out = evaluate(self.freeze, self.internal, self.protocols, mutant)
        self.assertFalse(out["precondition_reduction_proved"])
        self.assertIn("FULL_POPULATION_SELECTOR_OR_MINIMUM_THRESHOLD_NOT_PROVED", out["errors"])

    def test_scope_mapping_remains_open(self):
        out = evaluate(self.freeze, self.internal, self.protocols, self.reduction)
        self.assertIn(
            "MAP_TOOLATHLON_REPRESENTED_DIMENSIONS_TO_FROZEN_TOOL_DISCOVERY_CONTRACT_WITHOUT_SCOPE_WEAKENING",
            out["remaining_preconditions"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
