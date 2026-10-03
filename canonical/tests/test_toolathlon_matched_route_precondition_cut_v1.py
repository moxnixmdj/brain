from __future__ import annotations

import copy
import unittest

from canonical.runtime import toolathlon_matched_route_precondition_cut_v1 as cut


class Tests(unittest.TestCase):
    def test_live_state_compresses_six_to_three_without_execution(self):
        out = cut.evaluate()
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertEqual(out["original_open_preconditions"], 6)
        self.assertTrue(out["checker_and_task_population_frozen"])
        self.assertTrue(out["proved_existing_atomic_inputs"])
        self.assertTrue(out["terminal_selector_frozen"])
        self.assertEqual(out["closed_zero_reality_count"], 2)
        self.assertEqual(out["absorbed_original_precondition_count"], 2)
        self.assertEqual(out["minimum_remaining_fact_count"], 3)
        self.assertFalse(out["terminal_execution_authorized"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_tree_identity_is_load_bearing(self):
        freeze = cut._load(cut.FREEZE)
        freeze = copy.deepcopy(freeze)
        freeze["benchmark_identity"]["finalpool_tree_sha"] = "DRIFT"
        out = cut.evaluate(freeze=freeze)
        self.assertEqual(out["status"], "FAIL_CLOSED__PRECONDITION_CUT_INVALID")
        self.assertIn("CHECKER_OR_TASK_POPULATION_FREEZE_NOT_PROVED", out["errors"])

    def test_pre_task_candidate_freeze_is_load_bearing(self):
        freeze = cut._load(cut.FREEZE)
        freeze = copy.deepcopy(freeze)
        freeze["contamination_state"]["brain_candidate_frozen_before_task_prompt_content"] = False
        out = cut.evaluate(freeze=freeze)
        self.assertEqual(out["status"], "FAIL_CLOSED__PRECONDITION_CUT_INVALID")

    def test_existing_transfer_atom_must_remain_scope_complete(self):
        bindings = cut._load(cut.BINDINGS)
        bindings = copy.deepcopy(bindings)
        row = next(x for x in bindings["claims"] if x.get("predicate_id") == "TOOL_LEARNING_SECOND_TASK_TRANSFER")
        row["scope_complete"] = False
        out = cut.evaluate(bindings=bindings)
        self.assertIn("REQUIRED_EXISTING_TOOL_ATOMS_NOT_PROVED", out["errors"])

    def test_selector_cannot_execute_with_two_of_three(self):
        state = {x: True for x in cut.REMAINING}
        state[cut.REMAINING[-1]] = False
        out = cut.evaluate(remaining_pass=state)
        self.assertFalse(out["terminal_execution_authorized"])

    def test_selector_authorizes_only_all_three_independent_facts(self):
        state = {x: True for x in cut.REMAINING}
        out = cut.evaluate(remaining_pass=state)
        self.assertTrue(out["terminal_execution_authorized"])
        self.assertFalse(out["promotion_authority"])

    def test_selector_mutation_fails_closed(self):
        governance = cut._load(cut.CUT)
        governance = copy.deepcopy(governance)
        governance["terminal_selector"]["otherwise"] = "RUN_ANYWAY"
        out = cut.evaluate(cut=governance)
        self.assertIn("TERMINAL_SELECTOR_NOT_FAIL_CLOSED_OR_NOT_FROZEN", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
