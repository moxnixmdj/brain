from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

class R2PypiProvenanceDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.pypi_provenance_adequacy,"preflight")
    def test_family_is_reachable(self,preflight):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"pypi.provenance.audit_live_artifact","policy_id":"P",
            "goal_sha256":"a"*64,
            "selection_path":"canonical/selection.json",
            "metadata_path":"canonical/metadata.json",
            "report_path":"canonical/report.json"
        }
        out=direct.preflight({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.PYPI_PROVENANCE_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.pypi_provenance_adequacy,"run")
    @patch.object(direct.pypi_provenance_adequacy,"preflight")
    def test_verified_provenance_becomes_direct_adequacy(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"pypi.provenance.audit_live_artifact","policy_id":"P",
            "goal_sha256":"a"*64,
            "selection_path":"canonical/selection.json",
            "metadata_path":"canonical/metadata.json",
            "report_path":"canonical/report.json"
        }
        run.return_value={
            "pass":True,"capability_id":"pypi.provenance.audit_live_artifact",
            "selected_policy_id":"P","goal_sha256":"a"*64,
            "accepted_raw_obligation_ids":["RAWREQ:x"],
            "raw_acceptance_obligation_count":1,
            "acceptance_receipt":{"verified":True},
            "authority_boundary":"bounded pypi provenance"
        }
        out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])

    @patch.object(direct.pypi_provenance_adequacy,"run")
    @patch.object(direct.pypi_provenance_adequacy,"preflight")
    def test_failure_never_falls_through(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"pypi.provenance.audit_live_artifact","policy_id":"P",
            "goal_sha256":"a"*64,
            "selection_path":"canonical/selection.json",
            "metadata_path":"canonical/metadata.json",
            "report_path":"canonical/report.json"
        }
        run.return_value={"pass":False,"status":"FAIL_CLOSED","reason":"hash mismatch"}
        with patch.object(direct.http_json_observation_adequacy,"run") as observation, \
             patch.object(direct.typed_json_transform_adequacy,"run") as typed, \
             patch.object(direct.markdown_pdf_adequacy,"run") as pdf, \
             patch.object(direct.live_bound,"run_raw_goal") as legacy:
            out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        observation.assert_not_called(); typed.assert_not_called()
        pdf.assert_not_called(); legacy.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
