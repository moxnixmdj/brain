#!/usr/bin/env python3
"""Real-receipt tests for the verified-index and calculated-parameter law.

These tests do not invent tasks. They read the measured receipt produced from the
pinned real QuixBugs hard-open population and the project's existing receipts.
No external model, no network, no synthetic task, and no known-win retest.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

FROZEN_V2_HARD_OPEN_TASKS = [
    "breadth_first_search", "depth_first_search", "detect_cycle", "flatten",
    "kheapsort", "possible_change", "powerset", "reverse_linked_list",
    "shortest_path_length", "shortest_path_lengths", "shortest_paths",
    "shunting_yard", "sqrt", "subsequences", "topological_ordering", "wrap",
]
FROZEN_V2_KNOWN_WINS = [
    "bitcount", "bucketsort", "find_first_in_sorted", "find_in_sorted", "gcd",
    "get_factors", "hanoi", "is_valid_parenthesization", "knapsack", "kth",
    "lcs_length", "levenshtein", "lis", "longest_common_subsequence",
    "max_sublist_sum", "mergesort", "minimum_spanning_tree", "next_palindrome",
    "next_permutation", "pascal", "quicksort", "rpn_eval", "sieve", "to_base",
]
RECEIPT = ROOT / "canonical/verification/VERIFIED_INDEX_AND_CALCULATED_PARAMETER_ADMISSION_20261116_V1.json"
UNION = ROOT / "canonical/verification/PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
ANSWER = ROOT / "THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.md"
INTENT = ROOT / "canonical/action_intents/THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.json"


def load_receipt() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def load_union() -> dict:
    return json.loads(UNION.read_text(encoding="utf-8"))


class VerifiedIndexAndCalculatedParameterAdmissionTests(unittest.TestCase):
    def test_receipt_exists_and_audit_passes(self) -> None:
        data = load_receipt()
        self.assertEqual(
            data["schema"],
            "PROJECT_BRAIN_VERIFIED_INDEX_AND_CALCULATED_PARAMETER_ADMISSION_V1",
        )
        self.assertEqual(data["authority"], "NONE__PRODUCER_RUN_SANDBOX")
        self.assertTrue(data["audit_pass"])
        for name, passed in data["invariants"].items():
            self.assertTrue(passed, name)

    def test_hard_open_population_comes_from_real_published_tests(self) -> None:
        data = load_receipt()
        union = load_union()
        run = data["hard_open_test_integrity"]
        self.assertEqual(run["task_count"], 16)
        self.assertEqual(run["tasks"], FROZEN_V2_HARD_OPEN_TASKS)
        self.assertEqual(run["frozen_v2_population_count"], 16)
        self.assertEqual(run["current_union_receipt_hard_open_count"], union["hard_open_population_count"])
        self.assertEqual(run["current_union_receipt_hard_open_tasks"], union["hard_open_population_tasks"])
        self.assertEqual(run["external_repair_reclassification_credit"], "ZERO")
        self.assertEqual(run["frozen_v2_known_wins_not_retested"], sorted(FROZEN_V2_KNOWN_WINS))
        self.assertEqual(run["known_wins_retested"], 0)
        self.assertTrue(run["no_known_win_retested_as_progress"])
        self.assertTrue(set(run["tasks"]).isdisjoint(set(FROZEN_V2_KNOWN_WINS)))
        self.assertTrue(set(union["hard_open_population_tasks"]).issubset(set(run["tasks"])))
        self.assertTrue(run["no_synthetic_tasks"])
        self.assertTrue(run["published_test_files_present"])
        self.assertTrue(run["no_repair_claimed"])
        self.assertTrue(run["no_harness_integrity_failure"])
        self.assertEqual(run["total_collected_published_tests"], 85)
        self.assertEqual(run["total_invoked_published_tests"], 85)
        self.assertEqual(run["total_published_test_passes"], 22)
        self.assertEqual(run["total_published_test_failures"], 63)
        self.assertEqual(run["total_published_test_timeouts"], 6)
        self.assertEqual(run["total_published_test_skips"], 0)
        self.assertTrue(run["all_published_tests_collected_and_invoked"])
        self.assertTrue(run["no_hidden_skips"])

    def test_answer_keys_absent_and_every_published_test_is_hashed(self) -> None:
        data = load_receipt()
        run = data["hard_open_test_integrity"]
        self.assertTrue(run["answer_keys_absent"])
        self.assertEqual(run["answer_key_directories_found"], [])
        self.assertFalse(run["correct_flag_used"])
        self.assertTrue(run["published_test_bytes_hashed"])
        for row in run["rows"]:
            self.assertEqual(len(row["published_test_sha256"]), 64)
            self.assertTrue(row["published_test_file"].startswith("python_testcases/test_"))
            self.assertIn(row["returncode"], (0, 1))

    def test_pinned_quixbugs_and_only_our_system_ran_the_tests(self) -> None:
        data = load_receipt()
        self.assertEqual(data["upstream"], "https://github.com/jkoppel/QuixBugs")
        self.assertEqual(data["quixbugs_head"], "4257f44b0ff1181dedaedee6a447e133219fcebf")
        self.assertEqual(data["model_dependency_count"], 0)
        self.assertEqual(data["external_capability_provider_count"], 0)
        self.assertEqual(data["network_dependency_count"], 0)
        self.assertEqual(data["incremental_spend_usd"], 0)
        self.assertEqual(data["hard_open_test_integrity"]["external_model_calls"], 0)
        self.assertEqual(data["hard_open_test_integrity"]["network_calls_at_run_time"], 0)
        self.assertTrue(data["hard_open_test_integrity"]["pytest_plugin_autoload_disabled"])
        self.assertTrue(data["hard_open_test_integrity"]["no_test_file_edits"])
        self.assertFalse(data["hard_open_test_integrity"]["timeout_plugin_dependency"])
        self.assertTrue(pathlib.Path(data["hard_open_test_integrity"]["rows"][0]["pytest_python"]).is_file())

    def test_real_timeouts_are_isolated_not_harness_errors(self) -> None:
        data = load_receipt()
        run = data["hard_open_test_integrity"]
        sqrt = next(row for row in run["rows"] if row["task"] == "sqrt")
        self.assertEqual(sqrt["returncode"], 1)
        self.assertEqual(sqrt["collection_returncode"], 0)
        self.assertEqual(sqrt["collection_node_count"], 7)
        self.assertEqual(sqrt["invocation_row_count"], 7)
        self.assertEqual(len(sqrt["timeouts"]), 6)
        self.assertEqual(sqrt["counts"]["passed"], 1)
        self.assertEqual(sqrt["counts"]["failed"], 6)
        self.assertEqual(sqrt["counts"]["skipped"], 0)
        self.assertEqual(sqrt["harness_errors"], [])
        self.assertTrue(sqrt["no_harness_integrity_failure"])
        self.assertEqual(sqrt["status"], "PUBLISHED_TESTS_FAIL_OR_TIMEOUT__HARD_OPEN")
        for row in run["rows"]:
            self.assertEqual(row["collection_node_count"], row["invocation_row_count"])
            self.assertEqual(row["harness_errors"], [])
            self.assertTrue(row["no_harness_integrity_failure"])
            self.assertEqual(len(row["collection_nodeids"]), row["collection_node_count"])
        self.assertTrue(data["invariants"]["hard_open_timeouts_reported_as_failures_not_harness_errors"])
        self.assertTrue(data["invariants"]["all_published_tests_collected_and_invoked"])
        self.assertTrue(data["invariants"]["no_hidden_skips"])
        self.assertTrue(data["invariants"]["no_test_edits_or_timeout_plugin"])

    def test_three_blockers_are_bound_to_one_verified_index(self) -> None:
        data = load_receipt()
        self.assertEqual(
            data["answer"],
            "NO_SINGLE_SUFFICIENT_LEVER__HIGHEST_LEVERAGE_NECESSARY_CONDITION_IS_THE_VERIFIED_INDEX",
        )
        section = data["three_blockers_as_one_verified_index"]
        self.assertEqual(
            section["status"],
            "THREE_PROJECTIONS_OF_ONE_NECESSARY_CONDITION_NOT_A_SINGLE_SUFFICIENT_LEVER",
        )
        self.assertIn("chosen causal observation", section["identifiability"])
        self.assertIn("index key", section["vocabulary_insufficiency"])
        self.assertIn("execution verifier", section["synthesis_verification_asymmetry"])
        self.assertTrue(data["invariants"]["identifiability_is_not_one_demonstration"])
        self.assertTrue(data["invariants"]["vocabulary_insufficiency_requires_a_new_observable"])
        self.assertTrue(data["invariants"]["verified_index_lacks_the_policy_observable"])
        self.assertTrue(data["invariants"]["composition_needs_a_frame_and_proves_refusals"])

    def test_calculated_parameter_admission_is_zero_and_no_knowledge_house(self) -> None:
        data = load_receipt()
        section = data["calculated_parameter_admission"]
        self.assertEqual(section["status"], "ZERO_NEW_PARAMETERS__BEST_PART_IS_NO_PART")
        self.assertEqual(section["parameter_candidates_admitted"], 0)
        self.assertEqual(section["parameters_added"], 0)
        self.assertEqual(section["weights_touched"], 0)
        self.assertFalse(section["knowledge_house"])
        self.assertIn("b = C(s, o, I, V)", section["law"])
        self.assertEqual(section["existing_gate"], "canonical/swe_kernel/weight_update_admission_v1.py")
        facts = data["measured_facts"]["weight_fuel"]
        self.assertFalse(facts["ready_to_train"])
        self.assertEqual(facts["total_verified_units"], 64)
        self.assertEqual(facts["minimum_units_to_try"], 5000)

    def test_no_external_model_terminal_or_capability_credit(self) -> None:
        data = load_receipt()
        self.assertEqual(data["capability_credit"], "ZERO")
        self.assertEqual(data["terminal_credit"], "ZERO")
        self.assertFalse(data["independent_verification_completed"])
        for claim in (
            "NO_EXTERNAL_MODEL_CALLED",
            "NO_EXTERNAL_MODEL_WEIGHTS_OR_OUTPUTS",
            "NO_CONVENTIONAL_PRETRAINING",
            "NO_KNOWLEDGE_HOUSE_PARAMETERS",
            "NO_SENTIENCE_CLAIM",
            "NO_ALL_COMPUTER_USE_SOLVED_CLAIM",
            "NO_ADVANCED_SWE_SOLVED_CLAIM",
            "NO_SYNTHETIC_TASKS",
            "NO_KNOWN_WIN_RETESTED_AS_PROGRESS",
            "NO_EXTERNAL_REPAIR_RECLASSIFICATION_CREDIT",
            "NO_TEST_EDIT_OR_TIMEOUT_PLUGIN_SHORTCUT",
            "NO_SINGLE_SUFFICIENT_LEVER",
        ):
            self.assertIn(claim, data["hard_nonclaims"])

    def test_existing_organs_are_indexed_by_effect_and_all_present(self) -> None:
        data = load_receipt()
        self.assertEqual(data["organs_missing"], {})
        groups = data["organs_by_effect"]
        self.assertIn("canonical/runtime/applicability_v1.py", groups["identifiability_and_separation"])
        self.assertIn("canonical/tools/the_index_is_the_bottleneck_v1.py", groups["observable_and_vocabulary"])
        self.assertIn("canonical/swe_kernel/weight_update_admission_v1.py", groups["verifier_and_admission"])
        self.assertIn("canonical/tools/compose_measured_effects_v1.py", groups["composition_and_frame"])
        self.assertIn("canonical/runtime/compile_brain_unified_model_v1.py", groups["instant_knowledge_and_zero_weight_model"])

    def test_fresh_answer_and_intent_keep_terminal_truth_untouched(self) -> None:
        self.assertTrue(ANSWER.is_file())
        self.assertTrue(INTENT.is_file())
        answer = ANSWER.read_text(encoding="utf-8")
        intent = json.loads(INTENT.read_text(encoding="utf-8"))
        self.assertIn("fresh answer", answer)
        self.assertIn("Prompt-adherence matrix", answer)
        self.assertIn("YOU SURE THIS THE SMARTEST APPROACH?", answer)
        self.assertIn("2026-11-17 UTC", answer)
        self.assertIn("85/85 real published test node ids", answer)
        self.assertIn("zero external model calls", answer)
        self.assertIn("current main union receipt", answer)
        self.assertIn("zero external repair credit", answer)
        self.assertFalse(intent["truth"]["achieved"])
        self.assertEqual(intent["date"], "2026-11-17")
        self.assertEqual(intent["canonical_base_commit"], "98f60e7c87db0c1b042afa7ed71c381005209da6")
        self.assertEqual(intent["capability_credit_delta"], 0)
        self.assertEqual(intent["terminal_credit_delta"], 0)
        self.assertEqual(intent["model_calls"], 0)
        self.assertEqual(intent["network_calls"], 0)


if __name__ == "__main__":
    unittest.main()
