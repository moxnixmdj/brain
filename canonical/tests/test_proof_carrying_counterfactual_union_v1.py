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
    "bitcount", "bucketsort", "depth_first_search", "find_first_in_sorted",
    "find_in_sorted", "gcd", "get_factors", "hanoi",
    "is_valid_parenthesization", "knapsack", "kth", "lcs_length",
    "levenshtein", "lis", "longest_common_subsequence", "max_sublist_sum",
    "mergesort", "minimum_spanning_tree", "next_palindrome",
    "next_permutation", "pascal", "quicksort", "rpn_eval",
    "shortest_path_lengths", "sieve", "to_base",
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

    def test_only_the_clean_cross_corpus_arm_is_admitted(self) -> None:
        path = ROOT / "canonical" / "verification" / "QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        clean = mod.repaired_from_receipt(data)
        self.assertEqual(len(clean), 20)
        self.assertNotIn("detect_cycle", clean)
        self.assertIn("to_base", clean)
        self.assertEqual(
            mod.RECEIPT_ARMS_IGNORED[0]["arm"],
            "summary.all_other_fixes",
        )

    def test_mechanisms_are_indexed_by_effect_and_all_exist(self) -> None:
        census = mod.mechanism_census(ROOT)
        self.assertTrue(census["all_declared_mechanism_files_present"], census)
        self.assertIn("identification_and_separation", census["groups"])
        self.assertEqual(
            census["groups"]["hidden_synthesis_and_orchestration"]["missing"], []
        )
        self.assertIn(
            "canonical/tools/synthesized_expression_from_the_failure_v1.py",
            census["groups"]["constructive_actions_and_operands"]["present"],
        )
        self.assertIn(
            "canonical/swe_kernel/one_demonstration_identifies_v1.py",
            census["groups"]["identification_and_separation"]["present"],
        )
        self.assertIn(
            "canonical/tools/repair_where_the_suite_is_the_observable_v1.py",
            census["groups"]["independent_witness_and_admission"]["present"],
        )
        self.assertIn(
            "canonical/swe_kernel/repair_version_space_selection_v1.py",
            census["groups"]["identification_and_separation"]["present"],
        )
        self.assertIn(
            "canonical/tools/version_space_selection_measure_v1.py",
            census["groups"]["identification_and_separation"]["present"],
        )

    def test_newly_merged_evidence_was_read_before_the_answer(self) -> None:
        missing = [p for p in mod.EVIDENCE_READ if not (ROOT / p).is_file()]
        self.assertEqual(missing, [])
        self.assertIn(
            "THE_SPACE_IS_ASSEMBLED_NOT_LISTED_20261116_V1.md",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "canonical/verification/SYNTHESIS_FROM_THE_FAILURE_20261116_V1.json",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "WHAT_ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.md",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "canonical/verification/ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.md",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "canonical/verification/WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_20261116_V1.md",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "canonical/verification/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1.json",
            mod.EVIDENCE_READ,
        )

    def test_no_json_observable_gap_is_searchable_but_not_a_repair(self) -> None:
        path = ROOT / "canonical" / "verification" / "WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["tasks_measured"], 9)
        self.assertEqual(data["repaired"], 0)
        self.assertEqual(data["repaired_tasks"], [])
        self.assertEqual(data["stages"]["SCREEN_ACCEPTED__CORPUS_TEST_FAILS"], 3)
        self.assertIn("WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json", mod.REPAIR_RECEIPTS)

    def test_union_is_recorded_as_an_upper_bound_not_a_pytest_score(self) -> None:
        path = ROOT / "canonical" / "verification" / "PROOF_CARRYING_COUNTERFACTUAL_UNION_20261116_V1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            data["union_projection_status"]["status"],
            "UPPER_BOUND_UNTIL_COMPOSED_PYTEST_ONLY_RUN",
        )
        self.assertEqual(data["observable_gap_receipt"]["repaired"], 0)
        self.assertTrue(data["invariants"]["no_screen_only_verdict_counted_as_repair"])

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
