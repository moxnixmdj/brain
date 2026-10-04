from __future__ import annotations
import copy, unittest
from canonical.runtime.unknown_domain_direct_production_reducer_v1 import reduce_result,TRANSFER,ABSTAIN,CLAIM,LEASE

def good():
    rows=[]
    for i in range(12):
        rows.append({"case_id":f"T{i}","leaf_id":TRANSFER,"probe_count":2,"scorer_result":{"pass":True}})
    classes=["IDENTIFIABLE"]*5+["NONIDENTIFIABLE"]*5+["UNDERSPECIFIED"]*5
    for i,c in enumerate(classes):
        rows.append({"case_id":f"A{i}","leaf_id":ABSTAIN,"probe_count":1,"scorer_result":{"pass":True,"case_class":c}})
    return {
      "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_PRODUCTION_RESULT_V1",
      "status":"PRODUCTION_PASS",
      "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
      "authority_claim_id":CLAIM,
      "claim_create_http_status":201,
      "claim_uniqueness_source":"ATOMIC_CREATE_RESPONSE",
      "execution_lease_sha256":LEASE,
      "production_cases_generated":27,
      "persistent_learned_bytes":0,
      "external_frontier_model_calls":0,
      "external_learned_capability_calls":0,
      "incremental_spend_usd":0,
      "raw_hidden_records_persisted":False,
      "raw_evaluator_secret_persisted":False,
      "raw_beacon_persisted":False,
      "replay_allowed":False,
      "replacement_allowed":False,
      "promotion_authority":False,
      "separate_independent_reduction_required":True,
      "case_results":rows,
      "aggregate":{
        "transfer_leaf_pass":True,
        "abstention_leaf_pass":True,
        "all_27_cases_pass":True,
        "case_count":27,
        "class_balance":{"IDENTIFIABLE":5,"NONIDENTIFIABLE":5,"UNDERSPECIFIED":5},
        "separate_independent_reduction_required":True,
      }
    }

class Tests(unittest.TestCase):
    def test_good_is_candidate_only(self):
        out=reduce_result(good())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"PREDICATE_LOCAL_PROOF_CANDIDATE")
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])
    def test_one_case_failure_fails_closed(self):
        d=good(); d["case_results"][0]["scorer_result"]["pass"]=False
        self.assertFalse(reduce_result(d)["pass"])
    def test_duplicate_case_id_fails(self):
        d=good(); d["case_results"][1]["case_id"]=d["case_results"][0]["case_id"]
        self.assertFalse(reduce_result(d)["pass"])
    def test_probe_cap_is_load_bearing(self):
        d=good(); d["case_results"][0]["probe_count"]=3
        self.assertFalse(reduce_result(d)["pass"])
    def test_wrong_claim_fails(self):
        d=good(); d["authority_claim_id"]="bad"
        self.assertFalse(reduce_result(d)["pass"])
    def test_aggregate_balance_is_load_bearing(self):
        d=good(); d["aggregate"]["class_balance"]["IDENTIFIABLE"]=6
        self.assertFalse(reduce_result(d)["pass"])
    def test_raw_secret_persistence_fails(self):
        d=good(); d["raw_evaluator_secret_persisted"]=True
        self.assertFalse(reduce_result(d)["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
