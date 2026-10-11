from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_internal_top_support_bridge_v1 as bridge


def source(universal=True):
    return {
        "top_law_proved": True,
        "independent_or_formal": True,
        "top_law_universal_over_source_domain": universal,
        "source_domain_sha256": "a" * 64,
    }


def coverage():
    return {
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "official_task_count": 91,
        "source_domain_sha256": "a" * 64,
        "source_domain_exact_or_superset_of_target": True,
        "all_official_tasks_covered": True,
        "every_load_bearing_dimension_covered": True,
        "independent_or_formal": True,
        "load_bearing_dimensions": [
            "RUBRIC",
            "ANALYTICAL_QUALITY",
            "PRESENTATION",
        ],
        "private_task_contents_inferred": False,
    }


class AABriefcaseInternalTopSupportBridgeV1Tests(unittest.TestCase):
    def test_complete_universal_scope_bridge_passes(self):
        out = bridge.verify_internal_top_support_bridge(source(), coverage())
        self.assertTrue(out["aa_material_top_support_proved"])
        self.assertEqual(out["status"], "PASS__AA_MATERIAL_TOP_SUPPORT_SCOPE_BRIDGED")
        self.assertFalse(out["terminal_authority"])

    def test_current_30_case_selected_cell_fails_closed(self):
        out = bridge.current_selected_cell_probe()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["known_selected_cell_top_law_preserved"])
        self.assertFalse(out["aa_material_top_support_proved"])
        self.assertIn("TOP_LAW_UNIVERSAL_OVER_SOURCE_DOMAIN", out["reason"])

    def test_nonuniversal_source_top_law_rejected(self):
        with self.assertRaisesRegex(
            bridge.BridgeError,
            "TOP_LAW_UNIVERSAL_OVER_SOURCE_DOMAIN_NOT_PROVED",
        ):
            bridge.verify_internal_top_support_bridge(source(False), coverage())

    def test_partial_task_scope_rejected(self):
        c = coverage()
        c["all_official_tasks_covered"] = False
        with self.assertRaisesRegex(
            bridge.BridgeError,
            "ALL_OFFICIAL_TASKS_COVERED_NOT_PROVED",
        ):
            bridge.verify_internal_top_support_bridge(source(), c)

    def test_missing_presentation_dimension_rejected(self):
        c = coverage()
        c["load_bearing_dimensions"] = ["RUBRIC", "ANALYTICAL_QUALITY"]
        with self.assertRaisesRegex(
            bridge.BridgeError,
            "LOAD_BEARING_DIMENSIONS_INCOMPLETE",
        ):
            bridge.verify_internal_top_support_bridge(source(), c)

    def test_source_domain_mismatch_rejected(self):
        c = coverage()
        c["source_domain_sha256"] = "b" * 64
        with self.assertRaisesRegex(
            bridge.BridgeError,
            "SOURCE_DOMAIN_BINDING_MISMATCH",
        ):
            bridge.verify_internal_top_support_bridge(source(), c)

    def test_private_task_inference_rejected(self):
        c = coverage()
        c["private_task_contents_inferred"] = True
        with self.assertRaisesRegex(
            bridge.BridgeError,
            "PRIVATE_TASK_CONTENT_INFERENCE_FORBIDDEN",
        ):
            bridge.verify_internal_top_support_bridge(source(), c)

    def test_bridge_does_not_claim_elo(self):
        out = bridge.verify_internal_top_support_bridge(source(), coverage())
        self.assertIn(
            "THIS_BRIDGE_DOES_NOT_PROVE_A_FROZEN_CROWD_BT_ELO_FLOOR",
            out["hard_nonclaims"],
        )
        self.assertIn(
            "THIS_BRIDGE_DOES_NOT_BY_ITSELF_CERTIFY_AA_BRIEFCASE_GE_1822",
            out["hard_nonclaims"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
