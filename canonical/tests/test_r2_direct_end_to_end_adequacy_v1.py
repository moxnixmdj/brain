from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


GOAL = (
    "Create a tar.gz archive from the manifest canonical/tmp/manifest.json, "
    "including all its verification_paths files, and save it to "
    "canonical/tmp/output.tar.gz."
)

CODEC_GOAL = (
    "Create canonical/astra_runtime/tmp/R2_CODEC_SOURCE.json containing exactly "
    "three records with fields id and text: 1 alpha, 2 beta, 3 gamma. "
    "Encode those exact records as BSON and save "
    "canonical/astra_runtime/tmp/R2_CODEC_RECORDS.bson. "
    "Independently decode the BSON artifact using an implementation that is not "
    "provided by the BSON producer package, and verify the decoded records are "
    "exactly identical to canonical/astra_runtime/tmp/R2_CODEC_SOURCE.json in "
    "values, order, field names, and record count."
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


    def test_exact_literal_preflight_matches_without_execution(self):
        goal='Respond with exactly "READY_42".'
        with patch.object(direct.live_bound, "run_raw_goal") as execute:
            out=direct.preflight({"task_id":"t","goal":goal})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.EXACT_LITERAL_ROUTE_ID)
        self.assertIsNone(out["capability_id"])
        self.assertFalse(out["preflight_execution_authority"])
        execute.assert_not_called()

    def test_exact_literal_extra_unmodeled_text_does_not_match(self):
        out=direct.preflight({
            "task_id":"t",
            "goal":'Respond with exactly "READY_42". Then explain why.',
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"],"NO_DIRECT_ADEQUACY_ROUTE")

    @patch.object(direct.live_bound, "run_raw_goal")
    @patch.object(direct.literal_acceptance, "verify")
    def test_exact_literal_full_acceptance_is_direct_adequacy(self, verify, execute):
        goal='Reply with exactly OK.'
        pf=direct.preflight({"task_id":"t","goal":goal})
        execute.return_value={
            "pass":True,
            "raw_goal_sha256":pf["goal_sha256"],
            "raw_source_coverage_complete":True,
        }
        verify.return_value={
            "pass":True,
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "accepted_obligation_ids":["RAWREQ:x"],
            "required_obligation_count":1,
        }
        out=direct.run({"task_id":"t","goal":goal})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"],direct.EXACT_LITERAL_ROUTE_ID)
        self.assertFalse(out["retry_by_other_route_authorized"])
        execute.assert_called_once()
        verify.assert_called_once()

    def test_literal_json_preflight_matches_without_execution(self):
        goal=(
            "Create canonical/astra_runtime/tmp/R2_LITERAL.json containing exactly "
            "two records with fields id and name: 1 alpha; 2 beta"
        )
        with patch.object(direct.live_bound,"run_raw_goal") as execute:
            out=direct.preflight({"task_id":"t","goal":goal})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.LITERAL_JSON_ROUTE_ID)
        self.assertEqual(
            out["output_path"],
            "canonical/astra_runtime/tmp/R2_LITERAL.json",
        )
        execute.assert_not_called()

    @patch.object(direct.live_bound,"run_raw_goal")
    @patch.object(direct.literal_json_acceptance,"verify")
    def test_literal_json_full_acceptance_is_direct_adequacy(self,verify,execute):
        goal=(
            "Create canonical/astra_runtime/tmp/R2_LITERAL.json containing exactly "
            "one record with fields id and name: 1 alpha"
        )
        pf=direct.preflight({"task_id":"t","goal":goal})
        execute.return_value={
            "pass":True,
            "raw_goal_sha256":pf["goal_sha256"],
        }
        verify.return_value={
            "pass":True,
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "artifact_exact":True,
            "accepted_obligation_ids":["RAWREQ:x"],
            "required_obligation_count":1,
        }
        out=direct.run({"task_id":"t","goal":goal})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"],direct.LITERAL_JSON_ROUTE_ID)
        self.assertFalse(out["retry_by_other_route_authorized"])


    def test_structured_binary_preflight_matches_without_execution(self):
        with patch.object(direct.live_bound, "run_raw_goal") as execute:
            out = direct.preflight({"task_id": "t", "goal": CODEC_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.STRUCTURED_BINARY_ROUTE_ID)
        self.assertEqual(out["format"], "bson")
        self.assertEqual(out["capability_id"], "auto.pypi.bson-modern")
        self.assertFalse(out["preflight_execution_authority"])
        execute.assert_not_called()

    @patch.object(direct.live_bound, "run_raw_goal")
    @patch.object(direct.structured_binary_acceptance, "verify")
    def test_structured_binary_full_acceptance_is_direct_adequacy(self, verify, execute):
        pf = direct.preflight({"task_id": "t", "goal": CODEC_GOAL})
        execute.return_value = {
            "pass": True,
            "raw_goal_sha256": pf["goal_sha256"],
        }
        verify.return_value = {
            "pass": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "source_exact": True,
            "binary_present": True,
            "producer_output_verified": True,
            "independent_semantic_verification_verified": True,
            "accepted_obligation_ids": ["RAWREQ:a", "RAWREQ:b", "RAWREQ:c"],
            "required_obligation_count": 3,
        }
        out = direct.run({"task_id": "t", "goal": CODEC_GOAL})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(out["selected_policy_id"], direct.STRUCTURED_BINARY_ROUTE_ID)
        self.assertEqual(out["capability_id"], "auto.pypi.bson-modern")
        self.assertFalse(out["retry_by_other_route_authorized"])
        execute.assert_called_once()
        verify.assert_called_once()

    @patch.object(direct.live_bound, "run_raw_goal")
    @patch.object(direct.structured_binary_acceptance, "verify")
    def test_structured_binary_partial_acceptance_never_becomes_adequacy(self, verify, execute):
        pf = direct.preflight({"task_id": "t", "goal": CODEC_GOAL})
        execute.return_value = {
            "pass": True,
            "raw_goal_sha256": pf["goal_sha256"],
        }
        verify.return_value = {
            "pass": False,
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "accepted_obligation_ids": [],
            "required_obligation_count": 3,
        }
        out = direct.run({"task_id": "t", "goal": CODEC_GOAL})
        self.assertFalse(out["pass"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        self.assertEqual(
            out["status"],
            "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
