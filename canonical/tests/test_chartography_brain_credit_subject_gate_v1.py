from __future__ import annotations

import unittest

from canonical.runtime.chartography_brain_credit_subject_gate_v1 import (
    ChartographyCreditSubjectError,
    SUBJECT_SCHEMA,
    admit_brain_credit_subject,
)


def base_subject():
    return {
        "schema": SUBJECT_SCHEMA,
        "repository": "moxnixmdj/brain",
        "operative_solver_role": "BRAIN_OWNED_NATIVE_MECHANISM",
        "brain_owned_operative_artifact": True,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "producer_cognition_provenance_complete": True,
        "runtime_dependency_inventory_complete": True,
        "model_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "donor_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "acquisition_donor_used": False,
        "qualification_after_donor_removal": True,
        "student_or_derived_artifact_distinct_from_donor": True,
    }


class ChartographyBrainCreditSubjectGateTests(unittest.TestCase):
    def test_native_brain_subject_passes_attribution_gate(self):
        out = admit_brain_credit_subject(base_subject())
        self.assertTrue(out["brain_credit_subject_admissible"])
        self.assertFalse(out["benchmark_score_proved"])

    def test_qwen_runtime_rejected_even_if_local_and_hashed(self):
        s = base_subject()
        s["cognition_dependency_class"] = "MODEL_ASSISTED"
        s["model_dependency_count"] = 1
        s["external_model_runtime_dependency_count"] = 1
        with self.assertRaises(ChartographyCreditSubjectError):
            admit_brain_credit_subject(s)

    def test_minicpm_runtime_rejected_even_if_zero_cost(self):
        s = base_subject()
        s["model_dependency_count"] = 1
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "MODEL_DEPENDENCY_COUNT_MUST_EQUAL_ZERO",
        ):
            admit_brain_credit_subject(s)

    def test_model_laundering_by_brain_owned_wrapper_rejected(self):
        s = base_subject()
        s["brain_owned_operative_artifact"] = True
        s["operative_solver_role"] = "BRAIN_OWNED_NATIVE_MECHANISM"
        s["external_model_runtime_dependency_count"] = 1
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "EXTERNAL_MODEL_RUNTIME_DEPENDENCY_COUNT_MUST_EQUAL_ZERO",
        ):
            admit_brain_credit_subject(s)

    def test_unknown_cognition_provenance_fails_closed(self):
        s = base_subject()
        s["producer_cognition_provenance_complete"] = False
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "PRODUCER_COGNITION_PROVENANCE_INCOMPLETE",
        ):
            admit_brain_credit_subject(s)

    def test_legitimate_transfer_passes_only_after_donor_removal(self):
        s = base_subject()
        s["operative_solver_role"] = "BRAIN_OWNED_DERIVED_MECHANISM"
        s["acquisition_donor_used"] = True
        out = admit_brain_credit_subject(s)
        self.assertTrue(out["brain_credit_subject_admissible"])

        s["donor_runtime_dependency_count"] = 1
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "DONOR_RUNTIME_DEPENDENCY_COUNT_MUST_EQUAL_ZERO",
        ):
            admit_brain_credit_subject(s)


if __name__ == "__main__":
    unittest.main()
