from __future__ import annotations
import unittest

from canonical.runtime.chartography_brain_credit_subject_gate_v3 import (
    ChartographyCreditSubjectError,
    SUBJECT_SCHEMA,
    admit_brain_credit_subject,
)

OCR = {
    "capability_id": "image.extract.ocr.tesseract",
    "classification": "VERIFIED_BRAIN_OWNED_BOUNDED_COMPONENT",
    "verification_path": "canonical/governance/TESSERACT_OCR_DEPENDENCY_ACCOUNTING_V1.json",
    "donor_runtime_required": False,
    "external_frontier_model_required": False,
}


def subject():
    return {
        "schema": SUBJECT_SCHEMA,
        "repository": "moxnixmdj/brain",
        "operative_solver_role": "BRAIN_OWNED_NATIVE_MECHANISM",
        "brain_owned_operative_artifact": True,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "producer_cognition_provenance_complete": True,
        "runtime_dependency_inventory_complete": True,
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "bounded_learned_components": [dict(OCR)],
        "bounded_learned_component_provenance_complete": True,
        "acquisition_donor_used": False,
        "qualification_after_donor_removal": True,
        "student_or_derived_artifact_distinct_from_donor": True,
    }


class ChartographyCreditSubjectGateV3Tests(unittest.TestCase):
    def test_exact_tesseract_sensor_is_admitted_without_terminal_credit(self):
        out = admit_brain_credit_subject(subject())
        self.assertTrue(out["brain_credit_subject_admissible"])
        self.assertEqual(
            out["bounded_learned_component_ids"],
            ["image.extract.ocr.tesseract"],
        )
        self.assertFalse(out["benchmark_score_proved"])
        self.assertFalse(out["capability_relation_proved"])
        self.assertFalse(out["terminal_authority"])

    def test_external_general_purpose_runtime_cognition_is_rejected(self):
        s = subject()
        s["cognition_dependency_class"] = "MODEL_ASSISTED"
        s["general_purpose_model_dependency_count"] = 1
        s["external_general_purpose_model_runtime_dependency_count"] = 1
        with self.assertRaises(ChartographyCreditSubjectError):
            admit_brain_credit_subject(s)

    def test_external_model_cannot_be_laundered_as_bounded_sensor(self):
        s = subject()
        s["bounded_learned_components"][0]["capability_id"] = "Qwen/Qwen3-VL-8B-Instruct-GGUF"
        with self.assertRaisesRegex(ChartographyCreditSubjectError, "NOT_ALLOWLISTED"):
            admit_brain_credit_subject(s)

    def test_donor_transfer_must_be_derived_and_donor_removed(self):
        s = subject()
        s["acquisition_donor_used"] = True
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "DONOR_DERIVED_SOLVER_ROLE_REQUIRED",
        ):
            admit_brain_credit_subject(s)
        s["operative_solver_role"] = "BRAIN_OWNED_DERIVED_MECHANISM"
        out = admit_brain_credit_subject(s)
        self.assertTrue(out["brain_credit_subject_admissible"])


if __name__ == "__main__":
    unittest.main()
