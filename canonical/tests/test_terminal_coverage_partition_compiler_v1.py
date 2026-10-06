from __future__ import annotations

import unittest

from canonical.runtime.terminal_coverage_partition_compiler_v1 import (
    CoveragePartitionError,
    classify_one,
    compile_partition,
)


class TerminalCoveragePartitionCompilerTests(unittest.TestCase):
    def test_default_preserves_31_current_obligations_and_grants_zero_credit(self):
        out = compile_partition()
        self.assertEqual(out["truth_obligation_count"], 31)
        self.assertEqual(out["truth_obligations_deleted"], 1)
        self.assertEqual(out["truth_obligations_closed_by_routing_alone"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_joint_optimum_requires_every_load_bearing_premise(self):
        base = {
            "complete_semantics_verified": True,
            "joint_optimum_verified": True,
            "hard_constraints_verified": True,
            "brain_owned_verified": True,
            "independent_verification_verified": True,
        }
        self.assertEqual(classify_one("x", base).route, "J")
        for key in tuple(base):
            broken = dict(base)
            broken[key] = False
            self.assertNotEqual(
                classify_one("x", broken).route,
                "J",
                msg=f"J incorrectly survived missing {key}",
            )

    def test_generator_requires_target_and_utility_transfer(self):
        base = {
            "generator_verified": True,
            "brain_transfer_verified": True,
            "target_transfer_verified": True,
            "utility_pullback_verified": True,
            "hard_constraints_transfer_verified": True,
            "ownership_transfer_verified": True,
            "independent_verification_verified": True,
        }
        self.assertEqual(classify_one("x", base).route, "G")
        for key in ("target_transfer_verified", "utility_pullback_verified"):
            broken = dict(base)
            broken[key] = False
            self.assertNotEqual(
                classify_one("x", broken).route,
                "G",
                msg=f"G incorrectly survived missing {key}",
            )

    def test_astra_transitivity_requires_exact_matched_semantics_and_ownership(self):
        base = {
            "brain_ge_astra_verified": True,
            "astra_ge_opus55_verified": True,
            "same_context_verified": True,
            "same_evaluator_verified": True,
            "same_tool_policy_verified": True,
            "same_hard_constraints_verified": True,
            "distribution_aware_order_verified": True,
            "transitivity_verified": True,
            "brain_owned_verified": True,
            "astra_absent_from_brain_execution_verified": True,
            "independent_verification_verified": True,
        }
        self.assertEqual(classify_one("x", base).route, "T")
        for key in tuple(base):
            broken = dict(base)
            broken[key] = False
            self.assertNotEqual(
                classify_one("x", broken).route,
                "T",
                msg=f"T incorrectly survived missing {key}",
            )

    def test_external_result_atom_is_only_scheduling_candidate_without_receipt(self):
        out = compile_partition()
        row = out["classifications"]["FINANCE_AGENT_V2_GE_58_59"]
        self.assertEqual(row["route"], "D")
        self.assertEqual(row["status"], "SCHEDULING_CANDIDATE__NO_CREDIT")
        self.assertFalse(row["terminal_credit"])

    def test_direct_verified_evidence_can_classify_D_but_still_no_automatic_terminal_credit(self):
        row = classify_one("x", {"direct_evidence_verified": True})
        self.assertEqual(row.route, "D")
        self.assertEqual(row.status, "PROVED_ROUTE_CANDIDATE")
        self.assertFalse(row.terminal_credit)

    def test_unknown_evidence_item_fails_closed(self):
        with self.assertRaises(CoveragePartitionError):
            compile_partition({"NOT_A_REAL_OBLIGATION": {}})

    def test_astra_capability_targets_are_calibration_only(self):
        out = compile_partition()
        self.assertEqual(out["astra_calibration_target_count"], 8)
        for row in out["astra_calibration_targets"].values():
            self.assertFalse(row["terminal_credit"])
            self.assertEqual(
                row["role"],
                "ASTRA_CALIBRATION_TARGET_NOT_TERMINAL_OBLIGATION",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
