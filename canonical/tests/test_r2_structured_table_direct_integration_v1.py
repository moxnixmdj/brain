from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


class R2StructuredTableDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.table_adequacy, "preflight")
    def test_structured_table_family_is_reachable_from_direct_preflight(self, preflight):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_STRUCTURED_TABLE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "a" * 64,
            "format": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        out = direct.preflight({"task_id": "table", "goal": "not another direct grammar"})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.STRUCTURED_TABLE_ROUTE_ID)
        self.assertEqual(out["capability_id"], "xlsx.table.create_from_json_records")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.table_adequacy, "run")
    @patch.object(direct.table_adequacy, "preflight")
    def test_structured_table_verified_acceptance_becomes_direct_adequacy(
        self, preflight, run
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_STRUCTURED_TABLE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "b" * 64,
            "format": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        run.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_STRUCTURED_TABLE_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "b" * 64,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "raw_acceptance_obligation_count": 1,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded table family",
        }
        out = direct.run({"task_id": "table", "goal": "not another direct grammar"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(
            out["selected_policy_id"],
            "BOUND_CAPABILITY_POLICY::xlsx::goal",
        )

    @patch.object(direct.table_adequacy, "run")
    @patch.object(direct.table_adequacy, "preflight")
    def test_structured_table_acceptance_failure_never_falls_through(
        self, preflight, run
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_STRUCTURED_TABLE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "xlsx.table.create_from_json_records",
            "policy_id": "BOUND_CAPABILITY_POLICY::xlsx::goal",
            "goal_sha256": "c" * 64,
            "format": "xlsx",
            "json_path": "canonical/source.json",
            "output_path": "canonical/out.xlsx",
        }
        run.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_TABLE_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.codec_adequacy, "run") as codec_run, \
             patch.object(direct.docx_adequacy, "run") as docx_run, \
             patch.object(direct.docx_json_adequacy, "run") as docx_json_run, \
             patch.object(direct.live_bound, "run_raw_goal") as legacy:
            out = direct.run({"task_id": "table", "goal": "not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        codec_run.assert_not_called()
        docx_run.assert_not_called()
        docx_json_run.assert_not_called()
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
