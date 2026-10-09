from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

class R2RorAuthorityIdentityDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.ror_authority_adequacy,"preflight")
    def test_family_is_reachable(self,preflight):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"source.authority.identity.ror","policy_id":"P",
            "goal_sha256":"a"*64,"input_path":"canonical/in.json",
            "candidate_host":"worldbank.org","output_path":"canonical/out.json"
        }
        out=direct.preflight({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.ROR_AUTHORITY_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.ror_authority_adequacy,"run")
    @patch.object(direct.ror_authority_adequacy,"preflight")
    def test_verified_identity_becomes_direct_adequacy(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"source.authority.identity.ror","policy_id":"P",
            "goal_sha256":"a"*64,"input_path":"canonical/in.json",
            "candidate_host":"worldbank.org","output_path":"canonical/out.json"
        }
        run.return_value={
            "pass":True,"capability_id":"source.authority.identity.ror",
            "selected_policy_id":"P","goal_sha256":"a"*64,
            "accepted_raw_obligation_ids":["RAWREQ:x"],
            "raw_acceptance_obligation_count":1,
            "acceptance_receipt":{"verified":True},
            "authority_boundary":"exact ROR authority identity"
        }
        out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])

    @patch.object(direct.ror_authority_adequacy,"run")
    @patch.object(direct.ror_authority_adequacy,"preflight")
    def test_failure_never_falls_through(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"source.authority.identity.ror","policy_id":"P",
            "goal_sha256":"a"*64,"input_path":"canonical/in.json",
            "candidate_host":"worldbank.org","output_path":"canonical/out.json"
        }
        run.return_value={"pass":False,"status":"FAIL_CLOSED","reason":"identity mismatch"}
        with patch.object(direct.knowledge_consistency_adequacy,"run") as knowledge, \
             patch.object(direct.unit_normalized_comparison_adequacy,"run") as unitcmp, \
             patch.object(direct.numeric_comparison_adequacy,"run") as numeric, \
             patch.object(direct.live_bound,"run_raw_goal") as legacy:
            out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        knowledge.assert_not_called(); unitcmp.assert_not_called()
        numeric.assert_not_called(); legacy.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
