from __future__ import annotations

from pathlib import Path
import importlib
import unittest

ROOT=Path(__file__).resolve().parents[2]
MODULE_PATH=ROOT/"canonical/runtime/professional_quality_base_domain_normal_form_v1.py"


class ProfessionalBaseDomainNormalFormV1Tests(unittest.TestCase):
    def test_current_professional_domain_factorization_is_exact_and_zero_credit(self):
        self.assertTrue(MODULE_PATH.is_file(), "base-domain normal-form runtime missing")
        m=importlib.import_module(
            "canonical.runtime.professional_quality_base_domain_normal_form_v1"
        )
        out=m.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_coordinate_count"],6)
        self.assertEqual(
            out["semantic_coordinates"],
            [
                "objective",
                "audience",
                "source_evidence",
                "artifact_type",
                "constraints",
                "current_draft_or_render",
            ],
        )
        self.assertEqual(out["profile_step_count"],9)
        self.assertEqual(out["target_compilation_step_count"],1)
        self.assertEqual(out["hard_defect_preflight_step_count"],1)
        self.assertEqual(out["proof_bound_remaining_step_count"],7)
        self.assertTrue(out["profile_step_partition_complete"])
        self.assertFalse(out["root_specific_domain_equivalence_proved"])
        self.assertFalse(out["whole_leaf_scope_complete"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_target_coordinate_drift_fails_closed(self):
        self.assertTrue(MODULE_PATH.is_file(), "base-domain normal-form runtime missing")
        m=importlib.import_module(
            "canonical.runtime.professional_quality_base_domain_normal_form_v1"
        )
        out=m.verify(
            repo_root=ROOT,
            expected_semantic_coordinates=(
                "objective","audience","source_evidence","artifact_type","constraints","WRONG"
            ),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"TARGET_COORDINATE_SET_MISMATCH")

    def test_profile_step_partition_overlap_fails_closed(self):
        self.assertTrue(MODULE_PATH.is_file(), "base-domain normal-form runtime missing")
        m=importlib.import_module(
            "canonical.runtime.professional_quality_base_domain_normal_form_v1"
        )
        out=m.verify(repo_root=ROOT, injected_preflight_step="COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PROFILE_STEP_PARTITION_OVERLAP_OR_GAP")


if __name__=="__main__":
    unittest.main(verbosity=2)
