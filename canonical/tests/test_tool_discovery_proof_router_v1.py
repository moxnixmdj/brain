from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_proof_router_v1 import route

POL={"independent_verified":True,"policy_version":"V6"}
IDS={"independent_verified":True,"identity_scope_complete":True}
LOW={"independent_verified":True}

class Tests(unittest.TestCase):
    def test_universal_region_routes_without_matched_reality(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True,"ambiguous_decision_relevant_routes":[]}
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,lower_bound_receipt=LOW)
        self.assertEqual(out["status"],"UNIVERSAL_REGION__NO_MATCHED_REALITY_NEEDED_FOR_THIS_PARTITION")
    def test_matched_region_is_minimal(self):
        p={"identity_scope_complete":True,"matched_comparator_required":True,"universal_proof_eligible":False,"ambiguous_decision_relevant_routes":[{"tool_id":"A"}]}
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,lower_bound_receipt=LOW)
        self.assertEqual(out["ambiguous_route_count"],1)
        self.assertIn("MATCHED_ONLY",out["status"])
    def test_unverified_policy_fails_closed(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True}
        bad=dict(POL); bad["independent_verified"]=False
        self.assertEqual(route(policy_receipt=bad,identity_scope_receipt=IDS,partition_result=p,lower_bound_receipt=LOW)["status"],"FAIL_CLOSED")
if __name__=="__main__": unittest.main(verbosity=2)
