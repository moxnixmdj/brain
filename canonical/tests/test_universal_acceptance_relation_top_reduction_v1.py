import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime.universal_acceptance_relation_top_reduction_v1 import verify_reduction

ROOT = pathlib.Path("/home/sprite")
SOURCES = [
    "canonical/governance/ACCEPTANCE_RELATION_UNCERTAINTY_NORMAL_FORM_20261007_V1.json",
    "canonical/governance/TOP_SEMANTIC_OVERAPPROXIMATION_SOUNDNESS_TRUTH_REPAIR_20261007_V1.json",
    "canonical/governance/MONOTONE_PROOF_CARRYING_SEMANTIC_REFINEMENT_THEOREM_20261007_V1.json",
    "canonical/governance/ADAPTIVE_ABSTRACT_POSITIVE_COVER_FIXED_POINT_THEOREM_20261007_V2.json",
    "canonical/governance/TERMINAL_EXECUTION_ROOT_20261007_V1.json",
    "canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json",
]


def copy_sources(root):
    for rel in SOURCES:
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


class AcceptanceRelationTopReductionTests(unittest.TestCase):
    def test_exact_current_sources_delete_oq_scope_completeness_prerequisite(self):
        out = verify_reduction(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["acceptance_relation_top_sound"])
        self.assertFalse(out["oq_scope_complete_classification_required"])
        self.assertEqual(out["only_live_universal_premise"], "ESCAPE_PROGRESS_TOTALITY")
        self.assertFalse(out["u_empty_authorized"])
        self.assertFalse(out["terminal_authority"])

    def test_source_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            copy_sources(root)
            p = root / SOURCES[0]
            p.write_text(p.read_text() + "\n")
            out = verify_reduction(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SOURCE_BINDING_INVALID")
        self.assertFalse(out["u_empty_authorized"])

    def test_top_is_initial_sound_state_not_positive_adequacy_claim(self):
        out = verify_reduction(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["initial_relation_overapproximation"], "TOP_ALL_ADMISSIBLE_LOAD_BEARING_ACCEPTANCE_RELATIONS")
        self.assertFalse(out["common_policy_over_top_proved"])
        self.assertFalse(out["escape_progress_totality_proved"])

    def test_refinement_may_only_add_proof_carrying_policy_changing_information(self):
        out = verify_reduction(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["monotone_truth_preservation_bound"])
        self.assertEqual(
            out["refinement_rule"],
            "ADD_ONLY_SOUND_PROOF_CARRYING_POLICY_CHANGING_CONSTRAINTS_AND_PRESERVE_R_STAR",
        )


if __name__ == "__main__":
    unittest.main()
