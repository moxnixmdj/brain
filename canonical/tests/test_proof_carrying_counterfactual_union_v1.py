"""Integrity tests for the hard-open population audit.

These tests read the repository's measured receipts and real mechanism files.
They do not invent a task, run a toy solver, or count an already-repaired bug as
progress. The tool's full corpus audit is run against a real QuixBugs clone by
its measurement command; that clone is deliberately not fabricated here.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical" / "tools" / "proof_carrying_counterfactual_union_v1.py"

_spec = importlib.util.spec_from_file_location("proof_carrying_union_audit", TOOL)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

EXPECTED_REPAIRED_UNION = (
    "bitcount", "bucketsort", "find_first_in_sorted", "find_in_sorted",
    "gcd", "get_factors", "hanoi", "is_valid_parenthesization", "knapsack",
    "kth", "lcs_length", "levenshtein", "lis", "longest_common_subsequence",
    "max_sublist_sum", "mergesort", "minimum_spanning_tree", "next_palindrome",
    "next_permutation", "pascal", "quicksort", "rpn_eval", "sieve", "to_base",
)


class HardOpenPopulationAuditTests(unittest.TestCase):
    def test_receipt_union_is_measured_from_the_tree(self) -> None:
        census = mod.receipt_census(ROOT)
        self.assertEqual(census["repaired_union"], list(EXPECTED_REPAIRED_UNION))
        self.assertTrue(all(row["status"] == "READ" for row in census["rows"]))
        self.assertEqual(
            [row["answer_keys_present"] for row in census["rows"]
             if row["answer_keys_present"] is not None],
            [0, 0],
        )

    def test_only_the_rerun_confirmed_arm_is_admitted(self) -> None:
        path = ROOT / "canonical" / "verification" / "RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(data["confirmed"]), 16)
        self.assertEqual(len(data["inapplicable"]), 4)
        self.assertEqual(data["screen_said_pass_runner_said_no_in_the_record"], 0)
        self.assertNotIn("depth_first_search", data["confirmed"])
        self.assertIn("to_base", data["confirmed"])
        self.assertIn("RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json", mod.REPAIR_RECEIPTS)
        self.assertNotIn("QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json", mod.REPAIR_RECEIPTS)
        self.assertEqual(
            {row["arm"] for row in mod.RECEIPT_ARMS_IGNORED},
            {"summary.all_other_fixes", "summary.another_benchmark"},
        )

    def test_mechanisms_are_indexed_by_effect_and_all_exist(self) -> None:
        census = mod.mechanism_census(ROOT)
        self.assertTrue(census["all_declared_mechanism_files_present"], census)
        self.assertIn("identification_and_separation", census["groups"])
        self.assertEqual(
            census["groups"]["hidden_synthesis_and_orchestration"]["missing"], []
        )
        for path in (
            "canonical/tools/synthesized_expression_from_the_failure_v1.py",
            "canonical/runtime/anchored_frame_v1.py",
            "canonical/tools/miniwob_contract_arm_arm_v1.py",
        ):
            self.assertIn(path, census["groups"]["constructive_actions_and_operands"]["present"])
        for path in (
            "canonical/swe_kernel/one_demonstration_identifies_v1.py",
            "canonical/swe_kernel/repair_version_space_selection_v1.py",
            "canonical/tools/version_space_selection_measure_v1.py",
        ):
            self.assertIn(path, census["groups"]["identification_and_separation"]["present"])
        for path in (
            "canonical/tools/repair_where_the_suite_is_the_observable_v1.py",
            "canonical/tools/rerun_the_learned_arms_repairs_v1.py",
        ):
            self.assertIn(path, census["groups"]["independent_witness_and_admission"]["present"])

    def test_newly_merged_evidence_was_read_before_the_answer(self) -> None:
        missing = [p for p in mod.EVIDENCE_READ if not (ROOT / p).is_file()]
        self.assertEqual(missing, [])
        for path in (
            "THE_SPACE_IS_ASSEMBLED_NOT_LISTED_20261116_V1.md",
            "WHAT_ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.md",
            "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.md",
            "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_20261116_V1.md",
            "RERUN_THE_REPAIRS_NOT_THE_CLAIM_20261116_V1.md",
            "ONE_RUN_THREE_VOCABULARIES_ONE_JUDGE_20261116_V1.md",
            "THE_INVARIANCE_IS_THE_REACH_20261116_V1.md",
            "THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md",
            "THE_PRICE_OF_A_NEW_ENVIRONMENT_20261116_V1.md",
            "canonical/verification/SYNTHESIS_FROM_THE_FAILURE_20261116_V1.json",
            "canonical/verification/ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json",
            "canonical/verification/WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json",
            "canonical/verification/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json",
            "canonical/verification/RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json",
            "canonical/verification/THE_ROW_WAS_ALWAYS_THERE_20261116_V1.json",
            "canonical/verification/COMPOSED_REPAIR_ONE_RUN_20261116_V1.json",
            "canonical/verification/ARM_LEARNED_IN_ONE_RUN_20261116_V1.json",
            "canonical/verification/WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json",
            "canonical/verification/THE_SENTENCE_DID_NOT_HAVE_TO_SAY_SUBMIT_20261116_V1.json",
            "canonical/verification/INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json",
            "canonical/verification/INSTANT_LEARNING_SHUFFLED_CONTROL_20261116_V1.json",
            "THE_MISSING_PART_IS_THE_OPERAND_NOT_THE_EXPERIENCE_20261116_V1.md",
            "WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.md",
            "canonical/action_intents/READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json",
            "canonical/action_intents/THE_MISSING_PART_IS_THE_OPERAND_20261116_V1.json",
            "canonical/action_intents/WHY_LEARN_ONCE_REPLAY_FOREVER_FAILS_20261116_V1.json",
            "canonical/verification/ACTION_REPLAY_UNDER_CHANGE_20261116_V1.json",
            "canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json",
            "canonical/verification/LEARN_OR_READ_BOARD_20261116_V1.json",
            "canonical/verification/READ_FIRST_AND_LEARN_ONLY_FOR_A_NAMED_GAP_20261116_V1.json",
            "THERE_IS_NO_SINGLE_BOTTLENECK_AND_THE_TRIGGER_WAS_THE_REASON_20261116_V1.md",
            "ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md",
            "canonical/action_intents/THE_REMAINDER_IS_A_LONG_TAIL_20261116_V1.json",
            "canonical/action_intents/ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.json",
            "canonical/verification/DECLARED_TRIGGER_AND_OPERAND_TAXONOMY_20261116_V1.json",
            "canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json",
            "THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.md",
            "canonical/action_intents/THE_GUI_HAS_NO_INVARIANCE_TO_FIND_20261116_V1.json",
            "canonical/verification/GUI_INVARIANCE_IS_VACUOUS_OR_ABSENT_20261116_V1.json",
            "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.md",
            "COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json",
        ):
            self.assertIn(path, mod.EVIDENCE_READ)

    def test_no_json_observable_gap_is_searchable_but_not_a_repair(self) -> None:
        path = ROOT / "canonical" / "verification" / "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["tasks_measured"], 9)
        self.assertEqual(data["repaired"], 0)
        self.assertEqual(data["repaired_tasks"], [])
        self.assertEqual(data["stages"]["SCREEN_ACCEPTED__CORPUS_TEST_FAILS"], 3)
        self.assertIn("WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json", mod.REPAIR_RECEIPTS)

    def test_verified_union_is_24_and_the_projected_26_is_not_quoted(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["union_projection_status"]["status"],
            "ONE_COMPOSED_RUN_UNDER_THE_CORPUS_PYTEST_MEASURED_24_OF_40",
        )
        self.assertEqual(data["composed_run"]["repaired"], 24)
        self.assertEqual(data["composed_run"]["seconds"], 387.8)
        self.assertEqual(sum(len(v) for v in data["composed_run"]["by_arm"].values()), 24)
        self.assertEqual(data["composed_run"]["status"], "MEASURED_ONE_RUN_NOT_CAPABILITY_GAIN_OVER_THE_PYTEST_REJUDGED_UNION")
        self.assertEqual(data["repaired_union_count"], 24)
        self.assertEqual(data["hard_open_population_count"], 16)
        self.assertEqual(data["unmeasurable_without_published_input_output_examples_count"], 8)
        self.assertEqual(data["verified_repair_rerun"]["claimed_repaired"], 20)
        self.assertEqual(len(data["verified_repair_rerun"]["confirmed"]), 16)
        self.assertTrue(data["invariants"]["claimed_learned_arm_superseded_by_pytest_rerun"])
        self.assertTrue(data["invariants"]["verified_union_is_24_not_the_projected_26"])

    def test_new_mechanism_groups_are_present_by_effect(self) -> None:
        census = mod.mechanism_census(ROOT)
        self.assertTrue(census["all_declared_mechanism_files_present"], census)
        for group in (
            "exact_decision_past_enumeration",
            "invariance_and_in_run_learning",
            "environment_cost_and_composition",
            "read_first_operand_and_replay_drift",
            "long_tail_trigger_and_basin",
            "gui_invariance_and_operand_boundary",
            "proved_composition",
        ):
            self.assertIn(group, census["groups"])
            self.assertEqual(census["groups"][group]["missing"], [])
        for path in (
            "canonical/runtime/capability_planner.py",
            "canonical/runtime/generic_goal_tool_effect_planner_v1.py",
            "canonical/runtime/capability_composer_v1.py",
            "canonical/runtime/verified_skill_macro_planner_v1.py",
            "canonical/runtime/explicit_recovery_planner.py",
            "canonical/runtime/environment_learning_v1.py",
            "canonical/swe_kernel/predicate_world_abstraction_v1.py",
            "canonical/swe_kernel/operator_semantics_v1.py",
            "canonical/swe_kernel/hierarchical_skill_library_v1.py",
        ):
            self.assertIn(path, census["groups"]["environment_cost_and_composition"]["present"])

    def test_one_run_invariance_decision_browser_and_environment_are_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "composed_run_is_one_run_one_judge_24_of_40",
            "invariance_changes_reach_not_capability",
            "exact_decision_past_enumeration_wall_is_not_capability_credit",
            "browser_zero_experience_census_is_66_with_no_regressions",
            "new_environment_cost_law_is_bounded_and_shuffle_invariant",
        ):
            self.assertTrue(data["invariants"][key], key)
        self.assertEqual(data["invariance_and_reach"]["capability_gain_over_the_three_arm_composition"], 0)
        self.assertEqual(data["exact_decision_past_enumeration_wall"]["measured_effect"]["raw_survivors_pinned_corpus"], 8388600)
        self.assertEqual(data["browser_zero_experience_census"]["measured_effect"]["seed_1060"]["after"], 66)
        self.assertEqual(data["new_environment_cost_law"]["summary"]["requests_solved"], 13)
        self.assertEqual(data["new_environment_cost_law"]["shuffled_summary"]["requests_solved"], 13)
        self.assertIn("COMPOSED_REPAIR_ONE_RUN_20261116_V1.json", mod.REPAIR_RECEIPTS)
        self.assertIn("ARM_LEARNED_IN_ONE_RUN_20261116_V1.json", mod.REPAIR_RECEIPTS)
        self.assertNotIn("WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json", mod.REPAIR_RECEIPTS)

    def test_final_main_evidence_is_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "read_first_policy_is_measured_and_does_not_forbid_learning",
            "operand_addition_is_bounded_to_its_design_set",
            "replay_forever_is_falsified_by_state_drift",
        ):
            self.assertTrue(data["invariants"][key], key)
        section = data["read_first_operand_and_replay_drift"]
        self.assertEqual(
            section["status"],
            "READ_FIRST_FOR_A_NAMED_GAP_ADD_THE_MISSING_OPERAND_NEVER_REPLAY_A_PLAN_AS_A_MACRO",
        )
        self.assertEqual(section["read_first"]["composition_rule"]["LEARN_pages"], 41)
        self.assertEqual(section["read_first"]["composition_rule"]["READ_pages"], 89)
        self.assertEqual(section["read_first"]["composition_rule"]["READ_pages_reading_won"], 66)
        self.assertEqual(section["operand"]["transfer_boundary"]["held_out_pages"], 121)
        self.assertEqual(section["operand"]["transfer_boundary"]["shipped_solves"], 77)
        self.assertEqual(section["operand"]["transfer_boundary"]["union_solves"], 77)
        self.assertEqual(section["operand"]["addition_vs_shipped"]["chromium_seed_1060"]["gains"], 5)
        self.assertEqual(section["replay"]["arms"]["live_re_decision"]["pairs"], 228)
        self.assertEqual(section["replay"]["arms"]["replay_of_the_record"]["silent_corruption"], 71)
        self.assertEqual(section["replay"]["arms"]["replay_of_the_record"]["stale"], 122)
        self.assertIn("NO_REPLAY_FOREVER_ANYWHERE_CLAIM", data["hard_nonclaims"])
        self.assertIn("NO_CAPABILITY_REGISTERED", data["hard_nonclaims"])
        self.assertEqual(data["incremental_spend_usd"], 0)
        self.assertEqual(data["model_dependency_count"], 0)

    def test_final_main_long_tail_and_basin_are_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "declared_format_prior_is_too_small_to_be_a_single_lever",
            "the_unsolved_remainder_is_a_long_tail_not_one_bottleneck",
            "one_demonstration_learns_a_domain_not_the_environment",
        ):
            self.assertTrue(data["invariants"][key], key)
        section = data["long_tail_trigger_and_basin"]
        self.assertEqual(
            section["status"],
            "NO_SINGLE_LEVER_THE_REMAINDER_IS_A_LONG_TAIL_AND_THE_PREMISE_MUST_BE_OBSERVABLE",
        )
        self.assertEqual(section["declared_surface"]["pages_usable"], 123)
        self.assertEqual(section["declared_surface"]["pages_declaring_a_format"], 6)
        self.assertEqual(section["declared_surface"]["pages_with_no_typeable_field"], 84)
        self.assertEqual(section["taxonomy"]["classes"], 16)
        self.assertEqual(section["taxonomy"]["largest_class"], 6)
        self.assertEqual(section["taxonomy"]["pages_unsolved"], 46)
        self.assertEqual(section["basin"]["arms"]["status_level_goal"]["true_domain"], 112)
        self.assertEqual(section["basin"]["arms"]["premise_task_under_status"]["undecidable"], 24)
        self.assertEqual(section["basin"]["arms"]["premise_task_under_all_content"]["undecidable"], 0)
        self.assertEqual(section["basin"]["arms"]["command_output_control"]["undecidable"], 168)
        self.assertIn("NO_SINGLE_LEVER_CLAIM", data["hard_nonclaims"])
        self.assertIn("NO_ONE_DEMONSTRATION_PER_ENVIRONMENT_CLAIM", data["hard_nonclaims"])

    def test_final_gui_invariance_census_is_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "gui_identity_invariance_is_vacuous_by_construction",
            "gui_judge_has_no_task_equivalence_to_quotient",
            "phrase_blind_basis_adds_no_full_surface_capability",
        ):
            self.assertTrue(data["invariants"][key], key)
        section = data["gui_invariance_and_operand_boundary"]
        self.assertEqual(
            section["status"],
            "NO_GUI_INVARIANCE_LEVER_THE_REMAINING_BOUNDARY_IS_AN_OPERAND_NOT_ON_THE_PAGE",
        )
        self.assertEqual(section["identity_invariance"]["identity_arms"], 15)
        self.assertEqual(section["identity_invariance"]["identity_verdicts"]["INVARIANT"], 13)
        self.assertEqual(section["measured_effect"]["judge_pages_with_quotient_zero"], 4)
        self.assertEqual(section["phrase_blind_arm"]["gated_solved"], 9)
        self.assertEqual(section["phrase_blind_arm"]["blind_solved"], 5)
        self.assertEqual(section["phrase_blind_arm"]["blind_only"], [])
        self.assertEqual(section["measured_effect"]["phrase_blind_arm_design_set"]["blind_solved"], 4)
        self.assertIn("NO_GUI_INVARIANCE_LEVER", data["hard_nonclaims"])

    def test_final_four_levers_and_edit_supply_are_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        section = data["four_levers_and_edit_supply"]
        self.assertEqual(
            section["status"],
            "ONCE_IS_ARITHMETIC_AND_REAL_WORK_SUPPLY_IS_ABOUT_ONE_SIXTH",
        )
        self.assertIn("bits_after = log2(|H|/|G|)", section["law"])
        self.assertEqual(round(float(section["levers"]["bits_before"]), 4), 5.5546)
        self.assertEqual(round(float(section["levers"]["bits_after_one"]), 4), 3.8176)
        self.assertEqual(section["arithmetic"]["question_over_demonstration_ratio"], 1.747)
        self.assertEqual(section["arithmetic"]["state_name_arm"]["as_is"]["carried_model_survived"], 7)
        self.assertEqual(section["arithmetic"]["state_name_arm"]["renamed"]["carried_model_survived"], 0)
        self.assertEqual(section["supply"]["arms"]["supply"]["siblings_shape_only"], 43)
        self.assertEqual(section["supply"]["arms"]["supply"]["siblings_context_both"], 31)
        self.assertEqual(section["supply"]["arms"]["determinacy"]["pairs"], 245)
        self.assertEqual(section["supply"]["arms"]["determinacy"]["verbatim_repeats"], 103)
        self.assertEqual(section["supply"]["arms"]["determinacy"]["forced_by_the_demonstration"], 31)
        self.assertEqual(section["supply"]["arms"]["determinacy"]["wrong"], 64)
        self.assertTrue(data["invariants"]["one_demonstration_is_arithmetic_not_identification"])
        self.assertTrue(data["invariants"]["one_demonstration_amortises_only_a_sixth_of_real_work"])
        self.assertIn("NO_ONCE_IDENTIFIES_A_RULE", data["hard_nonclaims"])
        self.assertIn("NO_ONE_DEMONSTRATION_COVERS_MOST_REAL_WORK", data["hard_nonclaims"])
        self.assertIn("canonical/tools/the_four_levers_of_learning_from_experience_v1.py", mod.MECHANISM_GROUPS["four_levers_and_edit_supply"])
        self.assertIn("canonical/swe_kernel/systematic_edit_supply_v1.py", mod.MECHANISM_GROUPS["four_levers_and_edit_supply"])

    def test_final_proved_composition_is_read_without_credit(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["invariants"]["proved_composition_is_bounded_not_a_single_lever"])
        section = data["proved_composition"]
        self.assertEqual(
            section["status"],
            "COMPOSE_ONLY_WHAT_IS_PROVED_AFFIRMATIVE_ORGAN_IS_BOUNDED_NOT_A_SINGLE_LEVER",
        )
        self.assertEqual(section["boxes"]["COMPOSED_VERIFIED"], 31)
        self.assertEqual(section["boxes"]["PREMISE_DIED"], 22)
        self.assertEqual(section["boxes"]["B_REFUSED"], 27)
        self.assertEqual(section["boxes"]["NO_SECOND_CANDIDATE"], 34)
        self.assertEqual(section["reach"], {"compose": 0.3875, "where_premises_held": 0.5345})
        self.assertIn("NO_PROOF_COMPOSITION_AS_SINGLE_LEVER", data["hard_nonclaims"])

    def test_selection_measurement_is_read_but_not_counted_as_a_quixbugs_repair(self) -> None:
        path = ROOT / "canonical" / "verification" / "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["settled_and_equal_to_the_reference_behaviour"], 8)
        self.assertEqual(data["summary"]["regressions_caused_by_selection"], 0)
        self.assertEqual(
            data["why_majority_vote_is_not_a_selector"]["conclusion"],
            "self-consistency is not evidence; a labelled answer to a chosen input is",
        )
        self.assertNotIn(
            "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json",
            mod.REPAIR_RECEIPTS,
        )

    def test_corrected_browser_census_is_read_as_evidence_not_as_a_repair(self) -> None:
        path = ROOT / "canonical" / "verification" / "THE_ROW_WAS_ALWAYS_THERE_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["measured_effect"]["after"]["solved"], 52)
        self.assertEqual(data["measured_effect"]["after"]["refused"], 51)
        self.assertEqual(data["measured_effect"]["regressions"], [])
        self.assertIn(
            "canonical/verification/THE_ROW_WAS_ALWAYS_THERE_20261116_V1.json",
            mod.EVIDENCE_READ,
        )

    def test_this_audit_registers_no_capability_and_touches_no_truth(self) -> None:
        self.assertEqual(mod.MODEL_DEPENDENCY_COUNT, 0)
        self.assertEqual(mod.NETWORK_DEPENDENCY_COUNT, 0)
        self.assertEqual(mod.INCREMENTAL_SPEND_USD, 0)
        self.assertEqual(mod.AUTHORITY, "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT")
        self.assertEqual(
            mod.SCHEMA,
            "BRAIN_PROOF_CARRYING_COUNTERFACTUAL_UNION_AUDIT_V1",
        )


if __name__ == "__main__":
    unittest.main()
