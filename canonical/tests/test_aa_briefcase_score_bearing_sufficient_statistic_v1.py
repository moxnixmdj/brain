from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_score_bearing_sufficient_statistic_v1 import (
    PUBLIC_CONTRACT_BLOB,
    PUBLIC_CONTRACT_PATH,
    TraceError,
    verify_sufficient_statistic,
    verify_trace_substitution,
)


def sufficient_payload():
    trace = {
        "rubric": {"rows": []},
        "analytical_quality": {"rows": []},
        "presentation": {"rows": []},
        "judge_state": {"panels": []},
        "scorer_state": {"scopes": []},
    }
    return {
        "benchmark": "AA-Briefcase",
        "version": "1.1",
        "public_contract": {
            "path": PUBLIC_CONTRACT_PATH,
            "git_blob_sha": PUBLIC_CONTRACT_BLOB,
        },
        "all_rubric_verdicts_included": True,
        "all_analytical_pairwise_verdicts_included": True,
        "all_presentation_pairwise_verdicts_included": True,
        "all_judge_assignments_included": True,
        "all_per_scope_crowd_bt_eta_included": True,
        "rubric_synthetic_head_to_head_state_included": True,
        "all_score_bearing_comparison_rows_included": True,
        "scope_membership_included": True,
        "anchor_identity_and_rating_included": True,
        "fit_reference_parameters_included": True,
        "score_clamp_and_postfit_rules_included": True,
        "anchor_model": "GPT-5.5 (medium)",
        "anchor_elo": 1000,
        "score_bearing_trace": trace,
        "score_bearing_trace_sha256": None,
    }


def substitution_payload():
    return {
        "benchmark": "AA-Briefcase",
        "version": "1.1",
        "reference_model": "Claude Opus 5.5 Max",
        "frozen_reference_elo": 1822,
        "reference_subject_normalized_trace_sha256": "a" * 64,
        "candidate_subject_normalized_trace_sha256": "a" * 64,
        "non_subject_graph_sha256": "b" * 64,
        "scorer_state_sha256": "c" * 64,
        "scorer_equivariance_proof_sha256": "d" * 64,
        "same_frozen_non_subject_graph": True,
        "same_frozen_scorer_state": True,
        "mathematical_crowd_bt_label_equivariance_verified": True,
        "owner_implementation_equivariance_or_unique_fit_verified": False,
    }


class Tests(unittest.TestCase):
    def test_complete_score_bearing_trace_is_sufficient(self):
        out = verify_sufficient_statistic(sufficient_payload())
        self.assertTrue(out["verified"])
        self.assertTrue(out["scope_complete"])
        self.assertFalse(out["private_task_text_required_after_trace_is_bound"])
        self.assertFalse(out["submission_artifact_bytes_required_after_trace_is_bound"])

    def test_missing_pairwise_scope_fails(self):
        x = sufficient_payload()
        x["all_presentation_pairwise_verdicts_included"] = False
        with self.assertRaisesRegex(
            TraceError, "ALL_PRESENTATION_PAIRWISE_VERDICTS_INCLUDED"
        ):
            verify_sufficient_statistic(x)

    def test_wrong_anchor_fails(self):
        x = sufficient_payload()
        x["anchor_elo"] = 999
        with self.assertRaisesRegex(TraceError, "ANCHOR_ELO_MISMATCH"):
            verify_sufficient_statistic(x)

    def test_declared_trace_digest_must_match(self):
        x = sufficient_payload()
        x["score_bearing_trace_sha256"] = "0" * 64
        with self.assertRaisesRegex(TraceError, "TRACE_DIGEST_MISMATCH"):
            verify_sufficient_statistic(x)

    def test_identical_trace_without_owner_fit_invariance_stays_open(self):
        out = verify_trace_substitution(substitution_payload())
        self.assertEqual(out["status"], "OPEN_OWNER_IMPLEMENTATION_EQUIVARIANCE")
        self.assertFalse(out["threshold_1822_proved"])

    def test_trace_mismatch_fails(self):
        x = substitution_payload()
        x["candidate_subject_normalized_trace_sha256"] = "e" * 64
        with self.assertRaisesRegex(TraceError, "SUBJECT_NORMALIZED_TRACE_MISMATCH"):
            verify_trace_substitution(x)

    def test_missing_mathematical_equivariance_fails(self):
        x = substitution_payload()
        x["mathematical_crowd_bt_label_equivariance_verified"] = False
        with self.assertRaisesRegex(
            TraceError, "MATHEMATICAL_LABEL_EQUIVARIANCE_NOT_VERIFIED"
        ):
            verify_trace_substitution(x)

    def test_full_substitution_premises_derive_exact_1822(self):
        x = substitution_payload()
        x["owner_implementation_equivariance_or_unique_fit_verified"] = True
        out = verify_trace_substitution(x)
        self.assertTrue(out["score_equality_proved"])
        self.assertEqual(out["derived_candidate_elo"], 1822)
        self.assertTrue(out["threshold_1822_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
