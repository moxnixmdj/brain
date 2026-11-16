"""Integrity tests for the hard-open population audit.

These tests read the repository's measured receipts and real mechanism files.
They do not invent a task, run a toy solver, or count an already-repaired bug as
progress. The tool's full corpus audit is run against a real QuixBugs clone by
its measurement command; that clone is deliberately not fabricated here.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical" / "tools" / "proof_carrying_counterfactual_union_v1.py"

_spec = importlib.util.spec_from_file_location("proof_carrying_union_audit", TOOL)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

EXPECTED_REPAIRED_UNION = (
    "bitcount", "bucketsort", "find_first_in_sorted", "find_in_sorted", "gcd",
    "get_factors", "is_valid_parenthesization", "kth", "lcs_length", "lis",
    "longest_common_subsequence", "max_sublist_sum", "mergesort",
    "next_palindrome", "next_permutation", "pascal", "quicksort", "rpn_eval",
    "sieve",
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

    def test_mechanisms_are_indexed_by_effect_and_all_exist(self) -> None:
        census = mod.mechanism_census(ROOT)
        self.assertTrue(census["all_declared_mechanism_files_present"], census)
        self.assertIn("identification_and_separation", census["groups"])
        self.assertEqual(
            census["groups"]["hidden_synthesis_and_orchestration"]["missing"], []
        )

    def test_newly_merged_evidence_was_read_before_the_answer(self) -> None:
        missing = [p for p in mod.EVIDENCE_READ if not (ROOT / p).is_file()]
        self.assertEqual(missing, [])
        self.assertIn(
            "ONE_DEMONSTRATION_LEAVES_TEN_BITS_20261116_V1.md",
            mod.EVIDENCE_READ,
        )
        self.assertIn(
            "canonical/verification/IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json",
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
