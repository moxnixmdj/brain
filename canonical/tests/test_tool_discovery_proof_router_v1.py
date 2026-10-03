from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_proof_router_v1 import route,_sha

POL={"independent_verified":True,"policy_version":"V6"}
IDS={"independent_verified":True,"identity_scope_complete":True,"scope_relation":"EXACT"}
LOW={"independent_verified":True,"lower_bound_verified":True}

def receipt(p):
    return {"independent_verified":True,"partition_result_sha256":_sha(p)}

class Tests(unittest.TestCase):
    def test_universal_region_routes_without_matched_reality(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True,"ambiguous_decision_relevant_routes":[]}
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,partition_receipt=receipt(p),lower_bound_receipt=LOW)
        self.assertEqual(out["status"],"UNIVERSAL_REGION__NO_MATCHED_REALITY_NEEDED_FOR_THIS_PARTITION")

    def test_matched_region_is_minimal(self):
        p={"identity_scope_complete":True,"matched_comparator_required":True,"universal_proof_eligible":False,"ambiguous_decision_relevant_routes":[{"tool_id":"A"}]}
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,partition_receipt=receipt(p),lower_bound_receipt=LOW)
        self.assertEqual(out["ambiguous_route_count"],1)
        self.assertIn("MATCHED_ONLY",out["status"])

    def test_unverified_policy_fails_closed(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True}
        bad=dict(POL); bad["independent_verified"]=False
        self.assertEqual(route(policy_receipt=bad,identity_scope_receipt=IDS,partition_result=p,partition_receipt=receipt(p),lower_bound_receipt=LOW)["status"],"FAIL_CLOSED")

    def test_partition_receipt_must_bind_exact_result(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True}
        r=receipt(p); r["partition_result_sha256"]="sha256:"+"0"*64
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,partition_receipt=r,lower_bound_receipt=LOW)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH",out["failures"])

    def test_lower_bound_receipt_must_verify_theorem(self):
        p={"identity_scope_complete":True,"matched_comparator_required":False,"universal_proof_eligible":True}
        low=dict(LOW); low["lower_bound_verified"]=False
        out=route(policy_receipt=POL,identity_scope_receipt=IDS,partition_result=p,partition_receipt=receipt(p),lower_bound_receipt=low)
        self.assertEqual(out["status"],"FAIL_CLOSED")

if __name__=="__main__": unittest.main(verbosity=2)
