from __future__ import annotations

import unittest

from canonical.runtime.chartography_brain_credit_subject_gate_v2 import (
    ChartographyCreditSubjectError,
    SUBJECT_SCHEMA,
    admit_brain_credit_subject,
)


OCR = {
    "capability_id": "image.extract.ocr.tesseract.positioned.tsv",
    "classification": "VERIFIED_BRAIN_OWNED_BOUNDED_COMPONENT",
    "verification_path": "canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "dependency_accounting_path": "canonical/governance/TESSERACT_OCR_DEPENDENCY_ACCOUNTING_V1.json",
    "donor_runtime_required": False,
    "external_frontier_model_required": False,
}


def base_subject():
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
        "bounded_learned_components": [],
        "bounded_learned_component_provenance_complete": True,
        "acquisition_donor_used": False,
        "qualification_after_donor_removal": True,
        "student_or_derived_artifact_distinct_from_donor": True,
    }


class ChartographyBrainCreditSubjectGateV2Tests(unittest.TestCase):
    def test_native_zero_model_subject_passes(self):
        out = admit_brain_credit_subject(base_subject())
        self.assertTrue(out["brain_credit_subject_admissible"])
        self.assertEqual(out["bounded_learned_component_count"], 0)

    def test_exact_verified_bounded_tesseract_component_is_allowed(self):
        s = base_subject()
        s["bounded_learned_components"] = [dict(OCR)]
        out = admit_brain_credit_subject(s)
        self.assertEqual(
            out["bounded_learned_component_ids"],
            ["image.extract.ocr.tesseract.positioned.tsv"],
        )
        self.assertEqual(out["model_dependency_count"], 0)

    def test_qwen_runtime_cognition_is_rejected(self):
        s = base_subject()
        s["cognition_dependency_class"] = "MODEL_ASSISTED"
        s["general_purpose_model_dependency_count"] = 1
        s["external_general_purpose_model_runtime_dependency_count"] = 1
        with self.assertRaises(ChartographyCreditSubjectError):
            admit_brain_credit_subject(s)

    def test_external_model_cannot_be_laundered_as_bounded_component(self):
        s = base_subject()
        fake = dict(OCR)
        fake["capability_id"] = "Qwen/Qwen3-VL-8B-Instruct-GGUF"
        s["bounded_learned_components"] = [fake]
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "BOUNDED_LEARNED_COMPONENT_NOT_ALLOWLISTED",
        ):
            admit_brain_credit_subject(s)

    def test_tesseract_provenance_mismatch_fails_closed(self):
        s = base_subject()
        bad = dict(OCR)
        bad["external_frontier_model_required"] = True
        s["bounded_learned_components"] = [bad]
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "BOUNDED_LEARNED_COMPONENT_PROVENANCE_MISMATCH",
        ):
            admit_brain_credit_subject(s)

    def test_unknown_bounded_component_provenance_fails_closed(self):
        s = base_subject()
        s["bounded_learned_components"] = [dict(OCR)]
        s["bounded_learned_component_provenance_complete"] = False
        with self.assertRaisesRegex(
            ChartographyCreditSubjectError,
            "BOUNDED_LEARNED_COMPONENT_PROVENANCE_INCOMPLETE",
        ):
            admit_brain_credit_subject(s)

    def test_legitimate_donor_transfer_requires_derived_solver(self):
        s = base_subject()
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
