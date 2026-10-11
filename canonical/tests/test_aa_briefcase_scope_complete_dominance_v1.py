import unittest

from canonical.runtime.aa_briefcase_scope_complete_dominance_v1 import (
    DominanceCertificateError,
    canonical_set_sha256,
    verify_scope_complete_dominance,
)


def target(owner_key_binding=None):
    out = {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_OPUS55_CURRENT_OWNER_TARGET_V1",
        "target": {
            "benchmark": "AA-Briefcase v1.1",
            "model": "Claude Opus 5.5 (Max, Default Fallback)",
            "current_owner_elo": 1807,
            "observed_date": "2026-10-08",
        },
        "epoch_rule": {"current_epoch_minimum_opus55_target_elo": 1807},
    }
    if owner_key_binding is not None:
        out["owner_attestation_trust_anchor"] = owner_key_binding
    return out


def certificate():
    task_ids = [f"t{i:03d}" for i in range(91)]
    checks = []
    for i, task_id in enumerate(task_ids):
        if i % 3 == 0:
            checks.append({
                "check_id": f"c{i:03d}",
                "task_id": task_id,
                "route": "E_EXPLICIT_COMPLETE",
                "load_bearing": True,
                "semantic_receipt_sha256": "1" * 64,
                "complete_semantics_verified": True,
                "brain_at_objective_top": True,
            })
        elif i % 3 == 1:
            checks.append({
                "check_id": f"c{i:03d}",
                "task_id": task_id,
                "route": "M_HIDDEN_RESTRICTED_MONOTONE",
                "load_bearing": True,
                "semantic_receipt_sha256": "2" * 64,
                "monotone_class_complete_verified": True,
                "dominance_mode": "UNIVERSAL_TOP_SUPPORT",
                "brain_noninferior": True,
            })
        else:
            checks.append({
                "check_id": f"c{i:03d}",
                "task_id": task_id,
                "route": "U_DIRECT_TARGET_RELATION",
                "load_bearing": True,
                "target_relation_receipt_sha256": "3" * 64,
                "relation_kind": "PAIRWISE_PREFERENCE",
                "judge_panel_class": "PAIRWISE_PANEL",
                "assignment_coverage": "ACTUAL_OWNER_ASSIGNMENT",
                "owner_assignment_verified": True,
                "matched_pairwise_semantics_verified": True,
                "outcome": "TIE",
            })
    return {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_SCOPE_COMPLETE_DOMINANCE_CERTIFICATE_V1",
        "status": "VERIFIED_SCOPE_COMPLETE_DOMINANCE",
        "independent_or_owner_verified": True,
        "benchmark": "AA-Briefcase v1.1",
        "model": "Claude Opus 5.5 (Max, Default Fallback)",
        "matched_current_owner_epoch": True,
        "target_observed_date": "2026-10-08",
        "subject_sha256": "a" * 64,
        "opus_reference_subject_sha256": "b" * 64,
        "private_task_population_sha256": "c" * 64,
        "scope_manifest_sha256": "d" * 64,
        "verification_receipt_sha256": "e" * 64,
        "grading_protocol_manifest_git_blob_sha": "5c77f294e09d4933e3a3175c46af225b414f4702",
        "task_count": 91,
        "expected_check_count": len(checks),
        "checks": checks,
        "check_id_set_sha256": canonical_set_sha256([x["check_id"] for x in checks]),
        "task_id_set_sha256": canonical_set_sha256(task_ids),
        "scope_manifest_attests_complete_private_population": True,
        "no_omitted_load_bearing_checks": True,
    }


class T(unittest.TestCase):
    def test_pass_mixed_emu(self):
        out = verify_scope_complete_dominance(target(), certificate())
        self.assertEqual(out["status"], "PASS_SCOPE_COMPLETE_CURRENT_EPOCH_DOMINANCE")
        self.assertEqual(out["task_count"], 91)
        self.assertEqual(sum(out["route_counts"].values()), 91)
        self.assertTrue(out["brain_weakly_dominates_current_opus55_on_every_load_bearing_check"])
        self.assertFalse(out["numeric_elo_reconstruction_required"])
        self.assertFalse(out["official_owner_elo_claimed"])

    def test_opus_win_fails(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u["outcome"] = "OPUS_WIN"
        with self.assertRaisesRegex(DominanceCertificateError, "U_OPUS_WIN_OR_INVALID"):
            verify_scope_complete_dominance(target(), c)

    def test_pairwise_full_panel_rejects_one_opus_win(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u.pop("owner_assignment_verified")
        u.pop("outcome")
        u["assignment_coverage"] = "ALL_BOUND_PANEL_JUDGES"
        u["panel_complete_verified"] = True
        u["panel_outcomes"] = ["BRAIN_WIN", "TIE", "OPUS_WIN"]
        with self.assertRaisesRegex(DominanceCertificateError, "U_OPUS_WIN_OR_INVALID"):
            verify_scope_complete_dominance(target(), c)

    def test_pairwise_full_panel_all_noninferior_passes(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u.pop("owner_assignment_verified")
        u.pop("outcome")
        u["assignment_coverage"] = "ALL_BOUND_PANEL_JUDGES"
        u["panel_complete_verified"] = True
        u["panel_outcomes"] = ["BRAIN_WIN", "TIE", "BRAIN_WIN"]
        out = verify_scope_complete_dominance(target(), c)
        self.assertEqual(out["status"], "PASS_SCOPE_COMPLETE_CURRENT_EPOCH_DOMINANCE")

    def test_actual_owner_assignment_must_be_verified(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u["owner_assignment_verified"] = False
        with self.assertRaisesRegex(DominanceCertificateError, "U_OWNER_ASSIGNMENT_UNVERIFIED"):
            verify_scope_complete_dominance(target(), c)

    def test_full_panel_requires_three_outcomes(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u.pop("owner_assignment_verified")
        u.pop("outcome")
        u["assignment_coverage"] = "ALL_BOUND_PANEL_JUDGES"
        u["panel_complete_verified"] = True
        u["panel_outcomes"] = ["BRAIN_WIN", "TIE"]
        with self.assertRaisesRegex(DominanceCertificateError, "U_PAIRWISE_PANEL_OUTCOME_COUNT_INVALID"):
            verify_scope_complete_dominance(target(), c)

    def test_rubric_opus_strictly_better_fails(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u.pop("matched_pairwise_semantics_verified")
        u.pop("outcome")
        u["relation_kind"] = "BINARY_RUBRIC"
        u["judge_panel_class"] = "RUBRIC_PANEL"
        u["assignment_coverage"] = "ACTUAL_OWNER_ASSIGNMENT"
        u["owner_assignment_verified"] = True
        u["matched_rubric_semantics_verified"] = True
        u["brain_pass"] = False
        u["opus_pass"] = True
        with self.assertRaisesRegex(DominanceCertificateError, "U_RUBRIC_OPUS_STRICTLY_BETTER"):
            verify_scope_complete_dominance(target(), c)

    def test_rubric_fail_fail_is_noninferior(self):
        c = certificate()
        u = next(x for x in c["checks"] if x["route"] == "U_DIRECT_TARGET_RELATION")
        u.pop("matched_pairwise_semantics_verified")
        u.pop("outcome")
        u["relation_kind"] = "BINARY_RUBRIC"
        u["judge_panel_class"] = "RUBRIC_PANEL"
        u["matched_rubric_semantics_verified"] = True
        u["brain_pass"] = False
        u["opus_pass"] = False
        out = verify_scope_complete_dominance(target(), c)
        self.assertEqual(out["status"], "PASS_SCOPE_COMPLETE_CURRENT_EPOCH_DOMINANCE")

    def test_missing_task_fails(self):
        c = certificate()
        c["checks"][-1]["task_id"] = c["checks"][0]["task_id"]
        c["task_id_set_sha256"] = canonical_set_sha256(sorted(set(x["task_id"] for x in c["checks"])))
        with self.assertRaisesRegex(DominanceCertificateError, "TASK_COVERAGE_NOT_91"):
            verify_scope_complete_dominance(target(), c)

    def test_check_root_drift_fails(self):
        c = certificate()
        c["check_id_set_sha256"] = "f" * 64
        with self.assertRaisesRegex(DominanceCertificateError, "CHECK_ID_SET_ROOT_MISMATCH"):
            verify_scope_complete_dominance(target(), c)

    def test_m_without_complete_monotone_semantics_fails(self):
        c = certificate()
        m = next(x for x in c["checks"] if x["route"] == "M_HIDDEN_RESTRICTED_MONOTONE")
        m["monotone_class_complete_verified"] = False
        with self.assertRaisesRegex(DominanceCertificateError, "M_CLASS_NOT_COMPLETE"):
            verify_scope_complete_dominance(target(), c)

    def test_grading_protocol_drift_fails(self):
        c = certificate()
        c["grading_protocol_manifest_git_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(DominanceCertificateError, "GRADING_PROTOCOL_MANIFEST_DRIFT"):
            verify_scope_complete_dominance(target(), c)

    def test_stale_epoch_fails(self):
        c = certificate()
        c["target_observed_date"] = "2026-09-22"
        with self.assertRaisesRegex(DominanceCertificateError, "CERTIFICATE_TARGET_DATE_MISMATCH"):
            verify_scope_complete_dominance(target(), c)
