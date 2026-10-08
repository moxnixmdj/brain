from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


GOAL = (
    "Create a tar.gz archive from the manifest canonical/tmp/manifest.json, "
    "including all its verification_paths files, and save it to "
    "canonical/tmp/output.tar.gz."
)


class R2DirectEndToEndAdequacyV1Tests(unittest.TestCase):
    def test_exact_archive_goal_preflight_matches_without_execution(self):
        with patch.object(direct.live_bound, "run_raw_goal") as execute:
            out = direct.preflight({"task_id": "t", "goal": GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.ARCHIVE_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])
        self.assertEqual(
            out["bound_inputs"]["manifest_path"],
            "canonical/tmp/manifest.json",
        )
        execute.assert_not_called()

    def test_extra_unmodeled_text_does_not_match_exact_cell(self):
        out = direct.preflight({
            "task_id": "t",
            "goal": GOAL + " Also email it to somebody.",
        })
        self.assertFalse(out["pass"])
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NO_DIRECT_ADEQUACY_ROUTE")

    @patch.object(direct.live_bound, "run_raw_goal")
    def test_full_acceptance_is_direct_adequacy(self, execute):
        pf = direct.preflight({"task_id": "t", "goal": GOAL})
        execute.return_value = {
            "pass": True,
            "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
            "compiled_capability_id": direct.ARCHIVE_CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": 1,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "semantic_acceptance_complete": True,
            "raw_goal_acceptance": {
                "pass": True,
                "status": "PASS__EXACT_RAW_GOAL_ARCHIVE_ACCEPTED",
                "semantic_acceptance_complete": True,
                "accepted_obligation_ids": ["RAWREQ:x"],
            },
        }
        out = direct.run({"task_id": "t", "goal": GOAL})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertFalse(out["terminal_authority"])
        execute.assert_called_once()

    @patch.object(direct.live_bound, "run_raw_goal")
    def test_partial_acceptance_never_becomes_adequacy(self, execute):
        pf = direct.preflight({"task_id": "t", "goal": GOAL})
        execute.return_value = {
            "pass": True,
            "compiled_capability_id": direct.ARCHIVE_CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": 2,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "semantic_acceptance_complete": False,
            "raw_goal_acceptance": {
                "pass": False,
                "semantic_acceptance_complete": False,
                "accepted_obligation_ids": [],
            },
        }
        out = direct.run({"task_id": "t", "goal": GOAL})
        self.assertFalse(out["pass"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        self.assertEqual(
            out["status"],
            "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
