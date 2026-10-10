from __future__ import annotations

import unittest

from canonical.runtime import professional_quality_root_subject_binding_verify_v1 as v


BINDING = "canonical/governance/PROFESSIONAL_QUALITY_R1_ROOT_SUBJECT_BINDING_20261010_V1.json"


class ProfessionalQualityRootSubjectBindingVerifyV1Tests(unittest.TestCase):
    def test_current_r1_binding_passes_narrowly(self):
        out = v.verify_binding(BINDING)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "PASS__ROOT_BOUND_TO_EXACT_DECLARED_SYSTEM")
        self.assertEqual(out["root_id"], "R1_TARGET_SPECIFICATION")
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertEqual(
            out["subject_id"],
            "PROFESSIONAL_QUALITY_P1_V4_TARGET_BOUND_SYSTEM_20261010_V3",
        )
        self.assertEqual(
            out["subject_sha256"],
            "e7292fbe697c2dcd06fc2c4346fc3e3bb231428a6511a88d575c655dd0f0c53a",
        )
        self.assertEqual(
            out["semantic_support"]["scope_id"],
            "PQ::R1::TARGET_SEMANTICS::PROFESSIONAL_ARTIFACT_PLAN",
        )
        self.assertEqual(
            out["execution_support"]["scope_id"],
            "PQ::R1::TARGET_CONTRACT::STRUCTURAL_COMPLETENESS_GATE",
        )
        self.assertEqual(out["bridge"]["kind"], "R1_TARGET_BOUND_ROUTER_V4")
        self.assertEqual(out["bridge"]["inherited_tests_passed"], 21)
        self.assertFalse(out["global_subject_identity_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_binding_fails_closed(self):
        out = v.verify_binding(
            "canonical/governance/DOES_NOT_EXIST_ROOT_SUBJECT_BINDING.json"
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "BINDING_FILE_INVALID")
        self.assertFalse(out["root_subject_binding_authority"])


if __name__ == "__main__":
    unittest.main()
