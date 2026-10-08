from __future__ import annotations
import unittest
from unittest.mock import patch
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

class R2TypedJsonTransformDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.typed_json_transform_adequacy,"preflight")
    def test_family_is_reachable(self,preflight):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"json.query.jq","policy_id":"P",
            "goal_sha256":"a"*64,"spec_path":"canonical/spec.json",
            "input_path":"canonical/in.json","output_path":"canonical/out.json"
        }
        out=direct.preflight({"task_id":"t","goal":"not another exact grammar"})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["route_id"],direct.TYPED_JSON_TRANSFORM_ROUTE_ID)
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.typed_json_transform_adequacy,"run")
    @patch.object(direct.typed_json_transform_adequacy,"preflight")
    def test_verified_transform_becomes_direct_adequacy(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"json.query.jq","policy_id":"P",
            "goal_sha256":"a"*64,"spec_path":"canonical/spec.json",
            "input_path":"canonical/in.json","output_path":"canonical/out.json"
        }
        run.return_value={
            "pass":True,"capability_id":"json.query.jq","selected_policy_id":"P",
            "goal_sha256":"a"*64,"accepted_raw_obligation_ids":["RAWREQ:x"],
            "raw_acceptance_obligation_count":1,
            "acceptance_receipt":{"verified":True},
            "authority_boundary":"typed json transform family"
        }
        out=direct.run({"task_id":"t","goal":"not another exact grammar"})
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])

    @patch.object(direct.typed_json_transform_adequacy,"run")
    @patch.object(direct.typed_json_transform_adequacy,"preflight")
    def test_failure_never_falls_through(self,preflight,run):
        preflight.return_value={
            "matched":True,"status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
            "capability_id":"json.query.jq","policy_id":"P",
            "goal_sha256":"a"*64,"spec_path":"canonical/spec.json",
            "input_path":"canonical/in.json","output_path":"canonical/out.json"
        }
        run.return_value={"pass":False,"status":"FAIL_CLOSED","reason":"semantic mismatch"}
        with patch.object(direct.visual_code_adequacy,"run") as visual, \
             patch.object(direct.typed_decision_adequacy,"run") as decision, \
             patch.object(direct.table_adequacy,"run") as table, \
             patch.object(direct.codec_adequacy,"run") as codec, \
             patch.object(direct.live_bound,"run_raw_goal") as legacy:
            out=direct.run({"task_id":"t","goal":"not another exact grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        visual.assert_not_called(); decision.assert_not_called()
        table.assert_not_called(); codec.assert_not_called(); legacy.assert_not_called()

if __name__=="__main__":
    unittest.main(verbosity=2)
