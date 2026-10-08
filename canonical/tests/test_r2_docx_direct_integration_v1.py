from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


class R2DocxDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.docx_json_adequacy, "preflight")
    def test_docx_family_is_reachable_from_direct_preflight(self, preflight):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_JSON_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "docx.document.create_from_json_record",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "g" * 64,
            "json_path": "canonical/source.json",
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        out = direct.preflight(
            {"task_id": "docx", "goal": "not another direct grammar"}
        )
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.DOCX_JSON_ROUTE_ID)
        self.assertEqual(
            out["capability_id"],
            "docx.document.create_from_json_record",
        )
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.docx_json_adequacy, "run")
    @patch.object(direct.docx_json_adequacy, "preflight")
    def test_verified_docx_family_becomes_direct_adequacy(
        self, preflight, run_docx
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_JSON_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "docx.document.create_from_json_record",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "g" * 64,
            "json_path": "canonical/source.json",
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        run_docx.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_DOCX_JSON_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "docx.document.create_from_json_record",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "g" * 64,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "raw_acceptance_obligation_count": 1,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded docx family",
        }
        out = direct.run(
            {"task_id": "docx", "goal": "not another direct grammar"}
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(
            out["selected_policy_id"],
            "BOUND_CAPABILITY_POLICY::docx::goal",
        )
        self.assertFalse(out["retry_by_other_route_authorized"])

    @patch.object(direct.docx_json_adequacy, "run")
    @patch.object(direct.docx_json_adequacy, "preflight")
    def test_docx_failure_never_falls_through_to_legacy_execution(
        self, preflight, run_docx
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_DOCX_JSON_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "docx.document.create_from_json_record",
            "policy_id": "BOUND_CAPABILITY_POLICY::docx::goal",
            "goal_sha256": "g" * 64,
            "json_path": "canonical/source.json",
            "output_path": "canonical/report.docx",
            "intent_path": "canonical/report.docx.intent.json",
        }
        run_docx.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_DOCX_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.live_bound, "run_raw_goal") as legacy:
            out = direct.run(
                {"task_id": "docx", "goal": "not another direct grammar"}
            )
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
