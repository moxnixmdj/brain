import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime.professional_presentation_relation_cut_bridge_v1 import verify_bridge

ROOT = pathlib.Path("/home/sprite")
SOURCES = [
    "canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json",
    "canonical/governance/SHARED_PROFESSIONAL_PRESENTATION_QUALITY_FRONTIER_20261007_V1.json",
    "canonical/governance/PROFESSIONAL_PRESENTATION_PUBLIC_CONTRACT_INFORMATION_LOWER_BOUND_20261007_V1.json",
    "canonical/governance/AUTHENTICATED_PRESENTATION_PARETO_CAPABILITY_BINDING_20261007_V1.json",
    "canonical/governance/UNIVERSAL_ACCEPTANCE_RELATION_TOP_REDUCTION_20261008_V1.json",
]


def copy_sources(root):
    for rel in SOURCES:
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


class ProfessionalPresentationRelationCutBridgeTests(unittest.TestCase):
    def test_exact_sources_localize_one_shared_separator_frontier(self):
        out = verify_bridge(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["constructive_relation_uncertainty_witness"])
        self.assertFalse(out["public_contract_entails_strict_presentation_order"])
        self.assertTrue(out["brain_owned_pareto_calculus_available"])
        self.assertFalse(out["complete_official_dimension_relation_envelope_bound"])
        self.assertFalse(out["full_scope_presentation_top_law_bound"])
        self.assertFalse(out["common_policy_nonexistence_proved"])
        self.assertFalse(out["u_empty_authorized"])
        self.assertEqual(
            out["shared_frontier_id"], "PROFESSIONAL_PRESENTATION_QUALITY_V1"
        )

    def test_two_world_nonidentifiability_is_replayed_not_merely_asserted(self):
        out = verify_bridge(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["countermodel_replayed"])
        self.assertEqual(out["countermodel"]["public_observation_equal"], True)
        self.assertEqual(out["countermodel"]["left_order"], "A_STRICTLY_OVER_B")
        self.assertEqual(out["countermodel"]["right_order"], "B_STRICTLY_OVER_A")
        self.assertTrue(out["countermodel"]["strict_order_not_entailed"])

    def test_minimum_separator_classes_are_only_load_bearing_moves(self):
        out = verify_bridge(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["minimum_separator_classes"],
            [
                "SCOPE_COMPLETE_PRESENTATION_TOP_OR_DOMINANCE_LAW",
                "AUTHENTIC_TARGET_PRESENTATION_RELATION_INFORMATION",
            ],
        )
        self.assertEqual(
            out["next_root_action"],
            "SEARCH_EXISTING_BRAIN_POLICY_FOR_SCOPE_COMPLETE_TOP_OR_DOMINANCE_CERTIFICATE__ELSE_BIND_MINIMUM_AUTHENTIC_TARGET_RELATION_SEPARATOR",
        )

    def test_lower_bound_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            copy_sources(root)
            p = root / SOURCES[2]
            p.write_text(p.read_text() + "\n")
            out = verify_bridge(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SOURCE_BINDING_INVALID")

    def test_pareto_binding_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            copy_sources(root)
            p = root / SOURCES[3]
            p.write_text(p.read_text() + "\n")
            out = verify_bridge(repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SOURCE_BINDING_INVALID")

    def test_bridge_never_claims_no_possible_third_top_policy(self):
        out = verify_bridge(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["common_policy_nonexistence_proved"])
        self.assertTrue(out["stronger_top_law_remains_logically_possible"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main()
