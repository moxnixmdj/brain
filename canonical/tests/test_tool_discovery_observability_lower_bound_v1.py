from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_observability_lower_bound_v1 import prove,_sha

def pair():
    obs={"tools":[{"tool_id":"A","cost":1},{"tool_id":"B","cost":2}],"required":["CAP"]}
    d=_sha(obs)
    return {
      "public_observation":obs,
      "allowed_information_fields":["tools","required"],
      "hidden_worlds":[
        {"public_observation_sha256":d,"hidden_state":{"A":True,"B":True},"valid_terminal_actions":["A","B"],"least_cost_valid_terminal_actions":["A"]},
        {"public_observation_sha256":d,"hidden_state":{"A":False,"B":True},"valid_terminal_actions":["B"],"least_cost_valid_terminal_actions":["B"]},
      ],
    }

class Tests(unittest.TestCase):
    def test_indistinguishable_pair_proves_lower_bound(self):
        out=prove(pair()); self.assertTrue(out["universal_deterministic_valid_and_least_cost_proof_impossible"],out)
        self.assertTrue(out["matched_or_additional_information_required"])
    def test_public_observation_mismatch_fails(self):
        x=pair(); x["hidden_worlds"][1]["public_observation_sha256"]="sha256:"+"0"*64
        self.assertEqual(prove(x)["status"],"FAIL_CLOSED")
    def test_undeclared_public_observation_field_fails_closed(self):
        x=pair(); x["public_observation"]["secret_leak"]="X"
        out=prove(x)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"PUBLIC_OBSERVATION_FIELDS_DO_NOT_MATCH_ALLOWED_INFORMATION")

    def test_declared_but_missing_observation_field_fails_closed(self):
        x=pair(); x["allowed_information_fields"].append("not_present")
        out=prove(x)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"PUBLIC_OBSERVATION_FIELDS_DO_NOT_MATCH_ALLOWED_INFORMATION")

    def test_duplicate_allowed_field_fails_closed(self):
        x=pair(); x["allowed_information_fields"].append("tools")
        out=prove(x)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"ALLOWED_INFORMATION_FIELDS_INVALID_OR_DUPLICATE")

    def test_common_least_cost_action_means_no_lower_bound(self):
        x=pair(); x["hidden_worlds"][1]["valid_terminal_actions"]=["A","B"]; x["hidden_worlds"][1]["least_cost_valid_terminal_actions"]=["A"]
        out=prove(x); self.assertFalse(out["universal_deterministic_valid_and_least_cost_proof_impossible"])
        self.assertFalse(out["matched_or_additional_information_required"])
if __name__=="__main__": unittest.main(verbosity=2)
