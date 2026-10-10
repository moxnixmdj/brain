from fractions import Fraction
from unittest import mock
import unittest

from canonical.runtime import capability_first_scheduler_v1 as s


def capability_row(work_id: str, **overrides):
    row = {
        "work_id": work_id,
        "work_type": "CAPABILITY_BUILD",
        "expected_capability_gain_lcb": 6,
        "expected_efficiency_gain_lcb": 5,
        "expected_reliability_gain_lcb": 4,
        "reuse_breadth_lcb": 8,
        "generalization_lcb": 7,
        "success_probability_lcb": "4/5",
        "wall_clock_cost_ub": 2,
        "compute_cost_ub": 2,
        "memory_cost_ub": 1,
        "complexity_cost_ub": 1,
    }
    row.update(overrides)
    return row


def complete_new_primitive_row(work_id: str = "NEW_PRIMITIVE_ROW", **overrides):
    row = capability_row(
        work_id,
        new_primitive_claim=True,
        residual_resolution_mode="NEW_PRIMITIVE",
        exact_unsatisfied_predicate="EXACT_PREDICATE_P_REMAINS_UNSATISFIED",
        existing_mechanisms_searched=["MECH_A", "MECH_B"],
        existing_mechanism_rejections={
            "MECH_A": {
                "reason": "Fails the exact predicate on witness A.",
                "soundness_preserving": True,
            },
            "MECH_B": {
                "reason": "Cannot close the exact predicate without an unsound assumption.",
                "soundness_preserving": True,
            },
        },
        independent_missing_primitive_verification_id="VERIFY-MISSING-PRIMITIVE-001",
        minimum_new_primitive_scope={"predicate": "P", "scope": "minimal"},
        new_primitive_falsifier={"kind": "counterexample", "target": "P"},
        new_primitive_promotion_criteria=["independent_replay", "neighbor_case_pass"],
    )
    row.update(overrides)
    return row


class ReuseFirstResidualSchedulerTests(unittest.TestCase):
    def rank(self, rows, open_count=0):
        return s.rank_work(rows, checkpoint_open_obligation_count=open_count)

    def test_new_primitive_without_mode_is_demoted(self):
        row = complete_new_primitive_row()
        row.pop("residual_resolution_mode")
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["eligibility"], "DEMOTED_NEW_PRIMITIVE_REUSE_EXHAUSTION_INCOMPLETE")
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "RESIDUAL_RESOLUTION_MODE_NEW_PRIMITIVE_REQUIRED",
            out["reuse_first_missing_requirements"],
        )

    def test_new_primitive_without_existing_mechanism_search_is_demoted(self):
        row = complete_new_primitive_row()
        row["existing_mechanisms_searched"] = []
        row["existing_mechanism_rejections"] = {}
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "EXISTING_MECHANISMS_SEARCHED_REQUIRED",
            out["reuse_first_missing_requirements"],
        )

    def test_new_primitive_missing_one_rejection_record_is_demoted(self):
        row = complete_new_primitive_row()
        del row["existing_mechanism_rejections"]["MECH_B"]
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "EXISTING_MECHANISM_REJECTION_SET_MUST_MATCH_SEARCHED_SET",
            out["reuse_first_missing_requirements"],
        )
        self.assertIn(
            "REJECTION_RECORD_REQUIRED:MECH_B",
            out["reuse_first_missing_requirements"],
        )

    def test_rejection_must_explicitly_preserve_soundness(self):
        row = complete_new_primitive_row()
        row["existing_mechanism_rejections"]["MECH_A"]["soundness_preserving"] = False
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "SOUNDNESS_PRESERVING_REJECTION_REQUIRED:MECH_A",
            out["reuse_first_missing_requirements"],
        )

    def test_complete_verified_reuse_exhaustion_remains_eligible(self):
        out = self.rank([complete_new_primitive_row()])["ranked"][0]
        self.assertEqual(out["eligibility"], "ELIGIBLE")
        self.assertEqual(out["reuse_first_admission_status"], "VERIFIED_REUSE_EXHAUSTION_BOUND")
        self.assertEqual(out["reuse_first_existing_mechanism_count"], 2)
        self.assertEqual(out["reuse_first_verification_id"], "VERIFY-MISSING-PRIMITIVE-001")
        self.assertNotEqual(out["priority_score"], "0")

    def test_legacy_general_capability_row_preserves_existing_behavior(self):
        out = self.rank([capability_row("LEGACY_GENERAL")])["ranked"][0]
        self.assertEqual(out["eligibility"], "ELIGIBLE")
        self.assertFalse(out["new_primitive_claim"])
        self.assertEqual(
            out["reuse_first_admission_status"],
            "NOT_APPLICABLE__NO_EXPLICIT_NEW_PRIMITIVE_CLAIM",
        )
        self.assertNotEqual(out["priority_score"], "0")

    def test_non_new_resolution_mode_does_not_create_new_gate(self):
        row = capability_row(
            "ADAPT_EXISTING_ROW",
            residual_resolution_mode="ADAPT_EXISTING",
            exact_unsatisfied_predicate="P",
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["eligibility"], "ELIGIBLE")
        self.assertFalse(out["new_primitive_claim"])

    def test_complete_reuse_receipt_cannot_override_open_world_wake_gate(self):
        row = complete_new_primitive_row(
            frontier_class=s.OPEN_WORLD_EVIDENCE_FRONTIER,
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(
            out["eligibility"],
            "DEMOTED_OPEN_WORLD_EVIDENCE_FRONTIER_WITHOUT_CURRENT_CAPABILITY_DEFECT",
        )
        self.assertEqual(out["priority_score"], "0")

    def test_benchmark_bookkeeping_remains_demoted(self):
        row = capability_row(
            "BOOKKEEPING",
            work_type="BENCHMARK_INSTRUMENTATION",
            benchmark_role="BOOKKEEPING",
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["eligibility"], "DEMOTED_BENCHMARK_BOOKKEEPING")
        self.assertEqual(out["priority_score"], "0")

    def test_primary_capability_score_ordering_is_unchanged(self):
        strong = capability_row(
            "STRONG",
            expected_capability_gain_lcb=100,
            expected_efficiency_gain_lcb=100,
            expected_reliability_gain_lcb=100,
        )
        weak = complete_new_primitive_row(
            "WEAK_NEW",
            expected_capability_gain_lcb=1,
            expected_efficiency_gain_lcb=0,
            expected_reliability_gain_lcb=0,
        )
        out = self.rank([weak, strong])
        self.assertEqual(out["ranked"][0]["work_id"], "STRONG")
        self.assertTrue(out["new_primitive_claim_requires_verified_reuse_exhaustion"])

    def test_shared_cause_fanout_remains_secondary_tie_break(self):
        a = capability_row("A")
        b = capability_row("B")
        def fanout(raw):
            return (Fraction(2 if raw["work_id"] == "B" else 1), [raw["work_id"]])
        with mock.patch.object(s, "_shared_residual_fanout", side_effect=fanout):
            out = self.rank([a, b])
        self.assertEqual(out["ranked"][0]["work_id"], "B")
        self.assertEqual(out["ranked"][0]["priority_score"], out["ranked"][1]["priority_score"])

    def test_checkpoint_audit_remains_tertiary(self):
        a = capability_row("A")
        b = capability_row(
            "B",
            open_obligation_ids=["OPEN_A"],
            expected_obligation_discharge_lcb=1,
            expected_obligation_unlock_lcb=0,
        )
        with mock.patch.object(
            s, "_shared_residual_fanout", return_value=(Fraction(1), ["CAUSE"])
        ):
            out = self.rank([a, b], open_count=13)
        self.assertEqual(out["ranked"][0]["work_id"], "B")
        self.assertEqual(out["ranked"][0]["priority_score"], out["ranked"][1]["priority_score"])
        self.assertEqual(
            out["ranked"][0]["shared_residual_fanout_score"],
            out["ranked"][1]["shared_residual_fanout_score"],
        )
        self.assertNotEqual(out["ranked"][0]["checkpoint_audit_score"], "0")


    def test_non_new_declared_residual_requires_exact_unsatisfied_predicate(self):
        row = capability_row(
            "ADAPT_WITHOUT_PREDICATE",
            residual_resolution_mode="ADAPT_EXISTING",
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(
            out["eligibility"],
            "DEMOTED_REUSE_FIRST_CLASSIFICATION_INCOMPLETE",
        )
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "EXACT_UNSATISFIED_PREDICATE_REQUIRED",
            out["reuse_first_missing_requirements"],
        )

    def test_unsupported_residual_resolution_mode_fails_closed(self):
        row = capability_row(
            "UNKNOWN_RESOLUTION_MODE",
            residual_resolution_mode="MAGIC_NEW_SOLVER",
            exact_unsatisfied_predicate="P",
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(
            out["eligibility"],
            "DEMOTED_REUSE_FIRST_CLASSIFICATION_INCOMPLETE",
        )
        self.assertEqual(out["priority_score"], "0")
        self.assertIn(
            "RESIDUAL_RESOLUTION_MODE_UNSUPPORTED:MAGIC_NEW_SOLVER",
            out["reuse_first_missing_requirements"],
        )

    def test_supported_non_new_mode_is_classified_without_new_primitive_credit(self):
        row = capability_row(
            "VERIFY_EXISTING_ROW",
            residual_resolution_mode="VERIFY_EXISTING",
            exact_unsatisfied_predicate="P",
        )
        out = self.rank([row])["ranked"][0]
        self.assertEqual(out["eligibility"], "ELIGIBLE")
        self.assertTrue(out["residual_classification_declared"])
        self.assertFalse(out["new_primitive_claim"])
        self.assertEqual(
            out["reuse_first_admission_status"],
            "CLASSIFIED_REUSE_FIRST_RESOLUTION__VERIFY_EXISTING",
        )



if __name__ == "__main__":
    unittest.main(verbosity=2)
