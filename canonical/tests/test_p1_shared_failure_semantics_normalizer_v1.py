from __future__ import annotations
import copy,unittest
from canonical.runtime.p1_shared_failure_semantics_normalizer_v1 import normalize

def case():
    return {
      "surface_id":"T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
      "task":{
        "trajectory":[
          {"action_id":"A0","reads":[],"writes":["x"],"depends_on":[],"checks":[
            {"kind":"SCHEMA","id":"A0:SCHEMA","pass":False,"evidence":["receipt:A0"],"failure_semantics":"DIRECT_CONTRACT"}]},
          {"action_id":"A1","reads":["x"],"writes":["y"],"depends_on":["A0"],"checks":[
            {"kind":"INVARIANT","id":"A1:INVARIANT","pass":False,"evidence":["receipt:A1"],"failure_semantics":"DERIVED_UPSTREAM"}]}
        ],
        "terminal_failed_resources":["y"],
        "goal":"LOCALIZE"
      }
    }

class Tests(unittest.TestCase):
    def test_explicit_direct_and_derived_pass(self):
        out=normalize(case()); self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["direct_failed_check_count"],1)
        self.assertEqual(out["derived_failed_check_count"],1)
    def test_missing_semantics_fails_closed(self):
        c=case(); del c["task"]["trajectory"][0]["checks"][0]["failure_semantics"]
        self.assertEqual(normalize(c)["reason"],"FAILED_CHECK_FAILURE_SEMANTICS_MISSING")
    def test_empty_failed_evidence_fails_closed(self):
        c=case(); c["task"]["trajectory"][0]["checks"][0]["evidence"]=[]
        self.assertEqual(normalize(c)["reason"],"FAILED_CHECK_CAUSAL_RECEIPT_MISSING")
    def test_invalid_semantics_fails_closed(self):
        c=case(); c["task"]["trajectory"][0]["checks"][0]["failure_semantics"]="GUESSED"
        self.assertEqual(normalize(c)["reason"],"FAILED_CHECK_FAILURE_SEMANTICS_INVALID")
    def test_surface_identity_required(self):
        c=case(); c["surface_id"]=""
        self.assertEqual(normalize(c)["reason"],"SURFACE_ID_MISSING")

if __name__=="__main__": unittest.main(verbosity=2)
