from __future__ import annotations
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_p1_router_v10 as r


def state(verifier=None):
    final = {}
    if verifier is not None:
        final["material_totality_semantic_verifier"] = verifier
    return {
        r.base.base.SUBJECT_REF_KEY: {
            "path": "canonical/governance/v10.json",
            "git_blob_sha": "a" * 40,
        },
        r.base.base.STEP_BINDINGS_KEY: {
            r.base.base.FINAL_STEP: final,
        },
    }


def positive():
    return {
        "status": "ROUTE__P1_ORDINARY",
        "route": "P1",
        "final_step_outcome": "POSITIVE_CERTIFICATE",
        "positive_certification_authorized": True,
        "v9_executable_r12_totality_semantics_verified": True,
    }


class Tests(unittest.TestCase):
    @patch.object(r.base, "route")
    @patch.object(r, "_v10_subject_ok")
    def test_foreign_verifier_rejected_before_v9_execution(self, subject, v9):
        subject.return_value = {"pass": True}
        foreign = {
            "path": "canonical/runtime/foreign.py",
            "git_blob_sha": "f" * 40,
        }
        out = r.route(state(foreign), repo_root=".")
        self.assertEqual(
            out["reason"],
            "V10_UNAPPROVED_R12_TOTALITY_VERIFIER_REJECTED_PREEXECUTION",
        )
        v9.assert_not_called()

    @patch.object(r.base, "route")
    @patch.object(r, "_v10_subject_ok")
    def test_exact_verifier_reaches_v9_and_positive_is_preserved(self, subject, v9):
        subject.return_value = {"pass": True}
        v9.return_value = positive()
        out = r.route(state(r.approved_totality_verifier_ref()), repo_root=".")
        self.assertEqual(out["final_step_outcome"], "POSITIVE_CERTIFICATE")
        self.assertTrue(out["v10_exact_r12_totality_verifier_pinned"])
        v9.assert_called_once()

    @patch.object(r.base, "route")
    @patch.object(r, "_v10_subject_ok")
    def test_abstention_without_semantic_verifier_is_preserved(self, subject, v9):
        subject.return_value = {"pass": True}
        v9.return_value = {
            "status": "ABSTAIN",
            "route": "ABSTAIN",
            "positive_certification_authorized": False,
        }
        out = r.route(state(), repo_root=".")
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertFalse(out["v10_exact_r12_totality_verifier_pinned"])

    @patch.object(r.base, "route")
    @patch.object(r, "_v10_subject_ok")
    def test_positive_without_verifier_pin_fails_closed(self, subject, v9):
        subject.return_value = {"pass": True}
        v9.return_value = positive()
        out = r.route(state(), repo_root=".")
        self.assertEqual(
            out["reason"],
            "V10_POSITIVE_PATH_WITHOUT_PREEXECUTION_EXACT_VERIFIER_PIN",
        )

    def test_approved_ref_is_exact_content_address(self):
        self.assertEqual(
            r.approved_totality_verifier_ref(),
            {
                "path": r.APPROVED_TOTALITY_VERIFIER_PATH,
                "git_blob_sha": r.APPROVED_TOTALITY_VERIFIER_BLOB,
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
