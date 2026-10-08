from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

class R2ExplicitNumericComparisonDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.numeric_comparison_adequacy,"preflight")
    def test_family_is_reachable(self,preflight):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"evidence.claim_spec.bind.explicit_comparison.stdlib",
            "policy_id":"P","goal_sha256":"a"*64,
            "extraction_path":"canonical/evidence.json",
            "objective":"Engine A is higher than Engine B",
            "operator":"GT","expected_predicate":True,
            "output_path":"canonical/out.json"
        }
        out=direct.preflight({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.NUMERIC_COMPARISON_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.numeric_comparison_adequacy,"run")
    @patch.object(direct.numeric_comparison_adequacy,"preflight")
    def test_verified_comparison_becomes_direct_adequacy(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"evidence.claim_spec.bind.explicit_comparison.stdlib",
            "policy_id":"P","goal_sha256":"a"*64,
            "extraction_path":"canonical/evidence.json",
            "objective":"Engine A is higher than Engine B",
            "operator":"GT","expected_predicate":True,
            "output_path":"canonical/out.json"
        }
        run.return_value={
            "pass":True,
            "capability_id":"evidence.claim_spec.bind.explicit_comparison.stdlib",
            "selected_policy_id":"P","goal_sha256":"a"*64,
            "accepted_raw_obligation_ids":["RAWREQ:x"],
            "raw_acceptance_obligation_count":1,
            "acceptance_receipt":{"verified":True,"predicate":True},
            "authority_boundary":"explicit grounded numeric comparison"
        }
        out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])

    @patch.object(direct.numeric_comparison_adequacy,"run")
    @patch.object(direct.numeric_comparison_adequacy,"preflight")
    def test_failure_never_falls_through(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"evidence.claim_spec.bind.explicit_comparison.stdlib",
            "policy_id":"P","goal_sha256":"a"*64,
            "extraction_path":"canonical/evidence.json",
            "objective":"Engine A is higher than Engine B",
            "operator":"GT","expected_predicate":True,
            "output_path":"canonical/out.json"
        }
        run.return_value={"pass":False,"status":"FAIL_CLOSED","reason":"predicate mismatch"}
        with patch.object(direct.exact_claim_support_adequacy,"run") as claim, \
             patch.object(direct.pypi_provenance_adequacy,"run") as prov, \
             patch.object(direct.http_json_observation_adequacy,"run") as obs, \
             patch.object(direct.live_bound,"run_raw_goal") as legacy:
            out=direct.run({"task_id":"t","goal":"not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        claim.assert_not_called(); prov.assert_not_called()
        obs.assert_not_called(); legacy.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
