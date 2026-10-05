from __future__ import annotations

import unittest

from canonical.runtime.work_unit_validity_guard_v1 import (
    WorkUnitValidityError,
    compute_component_digest,
    evaluate_two_clock_lease,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SCHED_A = "1" * 64
SCHED_B = "2" * 64


class TwoClockValidityGuardTests(unittest.TestCase):
    def test_digest_is_order_independent(self):
        self.assertEqual(
            compute_component_digest({"b": SHA_B, "a": SHA_A}),
            compute_component_digest({"a": SHA_A, "b": SHA_B}),
        )

    def test_empty_dependency_set_fails_closed(self):
        with self.assertRaises(WorkUnitValidityError):
            compute_component_digest({})

    def test_unrelated_scheduler_churn_preserves_zero_reality_semantics(self):
        result = evaluate_two_clock_lease(
            expected_semantic_components={"a": SHA_A, "closure": SHA_C},
            current_semantic_components_map={"a": SHA_A, "closure": SHA_C},
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_B,
            dependency_closure_verified=True,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertTrue(result["semantic_valid"])
        self.assertTrue(result["semantic_reuse_allowed"])
        self.assertFalse(result["scheduler_current"])
        self.assertEqual(
            result["status"],
            "PASS__SEMANTIC_RESULT_REUSABLE__SCHEDULER_REPLAN_REQUIRED",
        )

    def test_semantic_dependency_drift_invalidates_result(self):
        result = evaluate_two_clock_lease(
            expected_semantic_components={"a": SHA_A, "closure": SHA_C},
            current_semantic_components_map={"a": SHA_B, "closure": SHA_C},
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            dependency_closure_verified=True,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertFalse(result["semantic_valid"])
        self.assertFalse(result["semantic_reuse_allowed"])
        self.assertEqual(result["status"], "FAIL_CLOSED__SEMANTIC_DEPENDENCY_DRIFT")

    def test_fresh_reality_stays_blocked_on_scheduler_drift(self):
        result = evaluate_two_clock_lease(
            expected_semantic_components={"a": SHA_A, "closure": SHA_C},
            current_semantic_components_map={"a": SHA_A, "closure": SHA_C},
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_B,
            dependency_closure_verified=True,
            work_class="FRESH_REALITY_ACTION",
        )
        self.assertTrue(result["semantic_valid"])
        self.assertTrue(result["semantic_reuse_allowed"])
        self.assertFalse(result["fresh_reality_gate_current"])
        self.assertEqual(
            result["status"], "FAIL_CLOSED__SCHEDULER_STALE_FOR_FRESH_REALITY"
        )

    def test_unverified_dependency_closure_never_passes(self):
        result = evaluate_two_clock_lease(
            expected_semantic_components={"a": SHA_A},
            current_semantic_components_map={"a": SHA_A},
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            dependency_closure_verified=False,
            work_class="ZERO_REALITY_DERIVATION",
        )
        self.assertEqual(
            result["status"], "FAIL_CLOSED__DEPENDENCY_CLOSURE_UNVERIFIED"
        )
        self.assertFalse(result["semantic_reuse_allowed"])

    def test_current_both_clocks_does_not_grant_authority(self):
        result = evaluate_two_clock_lease(
            expected_semantic_components={"a": SHA_A, "closure": SHA_C},
            current_semantic_components_map={"a": SHA_A, "closure": SHA_C},
            expected_scheduler_epoch_sha256=SCHED_A,
            current_scheduler_epoch_sha256=SCHED_A,
            dependency_closure_verified=True,
            work_class="FRESH_REALITY_ACTION",
        )
        self.assertEqual(result["status"], "PASS__SEMANTIC_AND_SCHEDULER_CURRENT")
        self.assertTrue(result["fresh_reality_gate_current"])
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["promotion_authority"])
        self.assertFalse(result["fresh_reality_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
