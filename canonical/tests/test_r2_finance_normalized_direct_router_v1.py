from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

class FinanceNormalizedRouterTests(unittest.TestCase):
    @patch.object(direct.finance_normalized_adequacy,"preflight")
    def test_finance_family_is_reachable(self,pf):
        pf.return_value={"matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED","capability_id":"decision.synthesis.typed.stdlib","policy_id":"finance-p","goal_sha256":"f"*64,"package_path":"canonical/p.json","decision_problem_path":"canonical/d.json","output_path":"canonical/o.json","leaf_id":"DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"}
        out=direct.preflight({"task_id":"f","goal":"finance normalized"})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.FINANCE_NORMALIZED_DECISION_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.finance_normalized_adequacy,"run")
    @patch.object(direct.finance_normalized_adequacy,"preflight")
    def test_finance_verified_result_becomes_direct_adequacy(self,pf,run):
        pf.return_value={"matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED","capability_id":"decision.synthesis.typed.stdlib","policy_id":"finance-p","goal_sha256":"f"*64,"package_path":"canonical/p.json","decision_problem_path":"canonical/d.json","output_path":"canonical/o.json","leaf_id":"DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"}
        run.return_value={"pass":True,"status":"PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED","capability_id":"decision.synthesis.typed.stdlib","selected_policy_id":"finance-p","goal_sha256":"f"*64,"accepted_raw_obligation_ids":["RAWREQ:x"],"raw_acceptance_obligation_count":1,"acceptance_receipt":{"verified":True},"authority_boundary":"bounded finance"}
        out=direct.run({"task_id":"f","goal":"finance normalized"})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertEqual(out["selected_policy_id"],"finance-p")

    @patch.object(direct.finance_normalized_adequacy,"run")
    @patch.object(direct.finance_normalized_adequacy,"preflight")
    def test_matched_finance_failure_does_not_fall_through(self,pf,run):
        pf.return_value={"matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED","capability_id":"decision.synthesis.typed.stdlib","policy_id":"finance-p","goal_sha256":"f"*64}
        run.return_value={"pass":False,"status":"OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY","reason":"forced"}
        with patch.object(direct.live_bound,"run_raw_goal") as legacy:
            out=direct.run({"task_id":"f","goal":"finance normalized"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        legacy.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
