from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_public_interface_outcome_superdomain_v1 import (
    EXPECTED_PUBLIC_CONTRACT_BLOB,
    EXPECTED_PUBLIC_CONTRACT_PATH,
    SuperdomainError,
    verify,
)


def valid_payload():
    return {
        "benchmark": "AA-Briefcase",
        "version": "1.1",
        "official_task_count": 91,
        "official_project_count": 4,
        "max_turns": 500,
        "public_contract": {
            "path": EXPECTED_PUBLIC_CONTRACT_PATH,
            "git_blob_sha": EXPECTED_PUBLIC_CONTRACT_BLOB,
            "verified_against_owner_methodology": True,
            "task_and_grading_interface_scope_complete": True,
        },
        "tasks_run_independently": True,
        "finite_scenario_overview_unrestricted": True,
        "finite_week_overview_unrestricted": True,
        "finite_task_description_unrestricted": True,
        "finite_expected_output_filename_list_unrestricted": True,
        "finite_shared_file_map_unrestricted": True,
        "finite_week_file_map_unrestricted": True,
        "all_documented_tool_trajectories_up_to_turn_limit_included": True,
        "all_finite_submission_file_bytes_included": True,
        "abandon_outcome_included": True,
        "rubric_schema_all_finite_hidden_binary_predicates_included": True,
        "rubric_verdict_alphabet_complete": True,
        "analytical_pairwise_verdict_alphabet_complete": True,
        "presentation_pairwise_verdict_alphabet_complete": True,
        "all_public_judge_panel_assignments_included": True,
        "crowd_bt_eta_full_unit_interval_included": True,
        "all_finite_score_bearing_comparison_graphs_included": True,
        "headline_rating_real_nonnegative_output_included": True,
        "documented_tools": [
            "code_exec",
            "finish",
            "abandon_task_finish",
            "view_image_optional",
        ],
        "rubric_verdict_alphabet": [0, 1],
        "pairwise_verdict_alphabet": ["A", "TIE", "B"],
        "crowd_bt_eta_interval": [0.0, 1.0],
    }


class Tests(unittest.TestCase):
    def test_complete_public_interface_superdomain_passes(self):
        out = verify(valid_payload())
        self.assertEqual(out["status"], "PASS_SCOPE_COMPLETE_SUPERDOMAIN")
        self.assertTrue(out["scope_complete"])
        self.assertTrue(out["verified"])
        self.assertFalse(out["material_order_complete"])
        self.assertFalse(out["brain_top_support_proved"])

    def test_hidden_task_content_need_not_be_enumerated(self):
        out = verify(valid_payload())
        self.assertTrue(out["covers_private_task_contents_without_enumeration"])
        self.assertTrue(
            out["covers_private_task_specific_rubric_predicates_as_opaque_predicates"]
        )

    def test_missing_arbitrary_hidden_rubric_predicates_fails(self):
        x = valid_payload()
        x["rubric_schema_all_finite_hidden_binary_predicates_included"] = False
        with self.assertRaisesRegex(
            SuperdomainError, "RUBRIC_SCHEMA_ALL_FINITE_HIDDEN_BINARY_PREDICATES"
        ):
            verify(x)

    def test_wrong_pairwise_alphabet_fails(self):
        x = valid_payload()
        x["pairwise_verdict_alphabet"] = ["A", "B"]
        with self.assertRaisesRegex(SuperdomainError, "PAIRWISE_ALPHABET_INVALID"):
            verify(x)

    def test_eta_subinterval_fails_scope_completeness(self):
        x = valid_payload()
        x["crowd_bt_eta_interval"] = [0.5, 1.0]
        with self.assertRaisesRegex(SuperdomainError, "ETA_INTERVAL_INVALID"):
            verify(x)

    def test_missing_optional_vision_branch_fails(self):
        x = valid_payload()
        x["documented_tools"].remove("view_image_optional")
        with self.assertRaisesRegex(
            SuperdomainError, "VISION_TOOL_OPTION_NOT_COVERED"
        ):
            verify(x)

    def test_wrong_public_contract_blob_fails(self):
        x = valid_payload()
        x["public_contract"]["git_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(
            SuperdomainError, "PUBLIC_CONTRACT_BLOB_MISMATCH"
        ):
            verify(x)

    def test_public_contract_scope_must_be_complete(self):
        x = valid_payload()
        x["public_contract"]["task_and_grading_interface_scope_complete"] = False
        with self.assertRaisesRegex(
            SuperdomainError, "PUBLIC_CONTRACT_SCOPE_NOT_COMPLETE"
        ):
            verify(x)

    def test_superdomain_does_not_claim_material_order(self):
        out = verify(valid_payload())
        self.assertFalse(out["material_order_complete"])
        self.assertFalse(out["hidden_judge_monotonicity_proved"])
        self.assertFalse(out["frozen_1822_score_monotonicity_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
